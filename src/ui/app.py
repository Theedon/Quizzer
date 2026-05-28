from __future__ import annotations

import asyncio
import math
import os
import tempfile
from pathlib import Path
from typing import IO, Any

from nicegui import app, events, ui

from ..core import configure_logging, logger, settings
from ..utils.export import export_quizzes_to_csv
from .runner import GenerationProgress, run_generation

PROVIDERS = ["openai", "google", "groq"]
PROVIDER_MODEL_FIELD = {
    "openai": "OPENAI_MODEL",
    "google": "GEMINI_MODEL",
    "groq": "GROQ_MODEL",
}
PROVIDER_KEY_LABEL = {
    "openai": "OpenAI API Key",
    "google": "Google API Key",
    "groq": "Groq API Key",
}

GREEN_PRIMARY = "#16a34a"
GREEN_DARK = "#15803d"
GREEN_ACCENT = "#22c55e"


def is_valid_pdf(content: IO[bytes]) -> bool:
    """Check if file content starts with the PDF magic bytes."""
    header = content.read(5)
    content.seek(0)
    return header == b"%PDF-"


def _model_for(provider: str) -> str:
    field = PROVIDER_MODEL_FIELD.get(provider)
    return getattr(settings, field, "") if field else ""


def _phase_label(p: GenerationProgress) -> str:
    return {
        "idle": "Ready",
        "ingesting": "Reading PDF…",
        "chunking": "Splitting into chunks…",
        "generating": "Generating quiz…",
        "aggregating": "Finalizing…",
        "done": "Done",
        "error": "Failed",
    }.get(p.phase, "Ready")


@ui.page("/")
def index() -> None:
    ui.colors(
        primary=GREEN_PRIMARY,
        secondary=GREEN_DARK,
        accent=GREEN_ACCENT,
        positive=GREEN_PRIMARY,
    )
    dark = ui.dark_mode(value=True)

    state: dict[str, Any] = {
        "pdf_path": None,
        "pdf_name": None,
        "progress": GenerationProgress(),
        "quizzes": [],
        "running": False,
        "provider": settings.MODEL_PROVIDER,
        "model": _model_for(settings.MODEL_PROVIDER),
        "concurrency": settings.GEN_CONCURRENCY,
        "api_key": "",
        "page": 0,
        "page_size": 10,
        "cancel_event": None,
    }

    # ============================================================
    # Refreshable views (must exist before any handler refs them)
    # ============================================================

    @ui.refreshable
    def progress_view() -> None:
        p: GenerationProgress = state["progress"]
        with ui.card().classes("w-full p-4"):
            ui.label(_phase_label(p)).classes("text-sm font-semibold text-primary")

            if p.phase in ("ingesting", "chunking"):
                ui.linear_progress(show_value=False).props(
                    "indeterminate color=primary rounded"
                ).classes("w-full")
            else:
                ui.linear_progress(value=p.fraction, show_value=False).props(
                    "color=primary rounded"
                ).classes("w-full")

            if p.phase == "idle":
                detail = ""
            elif p.phase == "ingesting":
                detail = "Preparing document..."
            elif p.phase == "chunking":
                detail = f"pages {p.total_pages}"
            else:
                detail = (
                    f"pages {p.total_pages} · "
                    f"chunks {p.chunks_done}/{p.total_chunks or '?'} · "
                    f"questions {len(p.quizzes)}"
                )
            ui.label(detail).classes("text-xs opacity-70")
            if p.phase == "error" and p.error:
                ui.label(f"Error: {p.error}").classes("text-xs text-negative")

    @ui.refreshable
    def cards_view() -> None:
        quizzes: list[dict] = state["quizzes"]
        with ui.row().classes("w-full items-center justify-between"):
            ui.label(f"Generated questions ({len(quizzes)})").classes(
                "text-sm font-semibold text-primary"
            )
            download_btn = ui.button(
                "Download CSV",
                icon="download",
                on_click=on_download,
            ).props("color=primary unelevated")
            if not quizzes:
                download_btn.disable()

        if not quizzes:
            ui.label(
                "Upload a PDF and click Generate to see questions here."
            ).classes("text-xs opacity-60")
            return

        page = state["page"]
        page_size = state["page_size"]
        start = page * page_size
        end = start + page_size

        for idx, quiz in enumerate(quizzes[start:end], start=start):
            _quiz_card(idx, quiz)

        if len(quizzes) > page_size:
            total_pages = math.ceil(len(quizzes) / page_size)
            with ui.row().classes("w-full items-center justify-center gap-4 mt-2"):
                ui.button(
                    icon="chevron_left",
                    on_click=lambda: (state.update(page=state["page"] - 1), cards_view.refresh()),
                ).props("flat dense round color=primary").bind_enabled_from(
                    state, "page", backward=lambda p: p > 0
                )
                ui.label(f"Page {page + 1} / {total_pages}").classes(
                    "text-xs opacity-70"
                )
                ui.button(
                    icon="chevron_right",
                    on_click=lambda: (state.update(page=state["page"] + 1), cards_view.refresh()),
                ).props("flat dense round color=primary").bind_enabled_from(
                    state, "page", backward=lambda p: p < total_pages - 1
                )

    def _quiz_card(idx: int, quiz: dict) -> None:
        with ui.card().classes("w-full p-4 gap-2"):
            with ui.row().classes("w-full items-center justify-between"):
                ui.label(f"Q{idx + 1}").classes(
                    "text-xs font-semibold text-primary"
                )
                with ui.row().classes("items-center gap-2"):
                    ui.label(f"page {quiz.get('page_number', '?')}").classes(
                        "text-xs opacity-60"
                    )
                    ui.button(
                        icon="delete",
                        on_click=lambda _e, i=idx: delete_quiz(i),
                    ).props("flat dense round color=negative").tooltip(
                        "Remove this question"
                    )

            ui.input(
                label="Question",
                value=quiz.get("question", ""),
            ).classes("w-full").props("outlined dense").on_value_change(
                lambda e, q=quiz: q.update(question=e.value)
            )

            with ui.row().classes("w-full no-wrap gap-2"):
                for letter in ("a", "b", "c", "d"):
                    ui.input(
                        label=f"Option {letter.upper()}",
                        value=quiz.get(f"option_{letter}", ""),
                    ).classes("grow").props("outlined dense").on_value_change(
                        lambda e, q=quiz, k=f"option_{letter}": q.update({k: e.value})
                    )

            with ui.row().classes("w-full items-center gap-3"):
                ui.label("Correct").classes("text-xs opacity-70")
                ui.radio(
                    ["A", "B", "C", "D"],
                    value=quiz.get("answer", "A"),
                ).props("inline dense color=primary").on_value_change(
                    lambda e, q=quiz: q.update(answer=e.value)
                )

            ui.textarea(
                label="Explanation",
                value=quiz.get("explanation", ""),
            ).classes("w-full").props("outlined dense autogrow").on_value_change(
                lambda e, q=quiz: q.update(explanation=e.value)
            )

    # ============================================================
    # Handlers
    # ============================================================

    async def on_generate() -> None:
        if state["running"]:
            return
        if not state["pdf_path"]:
            ui.notify("Upload a PDF first", type="warning")
            return
        if not state["api_key"].strip():
            ui.notify(
                f"{PROVIDER_KEY_LABEL.get(state['provider'], 'API key')} is required",
                type="warning",
            )
            return

        provider_chip.set_text(f"provider: {state['provider']}")

        state["running"] = True
        state["quizzes"] = []
        state["page"] = 0
        state["progress"] = GenerationProgress(phase="ingesting")
        state["cancel_event"] = asyncio.Event()
        generate_btn.disable()
        progress_view.refresh()
        cards_view.refresh()
        action_buttons.refresh()

        def push(snapshot: GenerationProgress) -> None:
            state["progress"] = snapshot
            if snapshot.phase in ("done", "error"):
                state["quizzes"] = [dict(q) for q in snapshot.quizzes]
            progress_view.refresh()

        try:
            await run_generation(
                state["pdf_path"],
                push,
                cancel_event=state["cancel_event"],
                provider=state["provider"],
                model_name=state["model"],
                concurrency=int(state["concurrency"]) or 1,
                api_key=state["api_key"].strip() or None,
            )
            if state["cancel_event"] and state["cancel_event"].is_set():
                ui.notify(
                    f"Cancelled — kept {len(state['quizzes'])} questions",
                    type="warning",
                )
            else:
                ui.notify(
                    f"Generated {len(state['quizzes'])} questions",
                    type="positive",
                )
        except Exception as exc:
            logger.exception("UI generation failed")
            ui.notify(f"Generation failed: {exc}", type="negative")
        finally:
            state["running"] = False
            state["cancel_event"] = None
            generate_btn.enable()
            progress_view.refresh()
            cards_view.refresh()
            action_buttons.refresh()

    def on_download() -> None:
        quizzes = state["quizzes"]
        if not quizzes:
            ui.notify("Nothing to export yet", type="warning")
            return

        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".csv", prefix="quiz_export_"
        ) as tmp:
            tmp_path = tmp.name

        path = export_quizzes_to_csv(quizzes, custom_filepath=tmp_path)
        if not path:
            ui.notify("Export failed — check logs", type="negative")
            return
        try:
            ui.download(path, filename=Path(path).name)
        finally:
            Path(path).unlink(missing_ok=True)

    def delete_quiz(idx: int) -> None:
        if 0 <= idx < len(state["quizzes"]):
            del state["quizzes"][idx]
            total_pages = max(1, math.ceil(len(state["quizzes"]) / state["page_size"]))
            state["page"] = min(state["page"], total_pages - 1)
            cards_view.refresh()

    def reset_all() -> None:
        if state["running"]:
            ui.notify(
                "Generation in progress — wait for it to finish", type="warning"
            )
            return
        if state["pdf_path"]:
            Path(state["pdf_path"]).unlink(missing_ok=True)
        state["pdf_path"] = None
        state["pdf_name"] = None
        state["page"] = 0
        state["quizzes"] = []
        state["progress"] = GenerationProgress()
        upload_status.set_text("No file selected")
        upload_status.classes(add="opacity-50")
        generate_btn.disable()
        progress_view.refresh()
        cards_view.refresh()

    async def on_upload(e: events.UploadEventArguments) -> None:
        from io import BytesIO

        raw = await e.file.read()
        if not is_valid_pdf(BytesIO(raw)):
            ui.notify("Uploaded file is not a valid PDF.", type="warning")
            return

        old_path = state["pdf_path"]
        if old_path:
            Path(old_path).unlink(missing_ok=True)

        filename = e.file.name
        suffix = Path(filename).suffix or ".pdf"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.close()
        await e.file.save(tmp.name)
        state["pdf_path"] = tmp.name
        state["pdf_name"] = filename
        upload_status.set_text(f"Loaded: {filename}")
        upload_status.classes(remove="opacity-50")
        generate_btn.enable()

    def on_provider_change(e: events.ValueChangeEventArguments) -> None:
        state["provider"] = e.value
        state["model"] = _model_for(e.value)
        state["api_key"] = ""
        model_input.set_value(state["model"])
        api_key_input.set_value("")
        api_key_input.props(f"label='{PROVIDER_KEY_LABEL.get(e.value, 'API Key')}'")
        provider_chip.set_text(f"provider: {state['provider']}")

    # ============================================================
    # UI build
    # ============================================================

    # ---------- top bar ----------
    with ui.header(elevated=True).classes("items-center justify-between bg-primary"):
        with ui.row().classes("items-center gap-3"):
            ui.icon("school").classes("text-2xl text-white")
            ui.label("Quizzer").classes("text-xl font-semibold text-white")
            ui.label("PDF → quiz CSV").classes("text-xs text-white/70")
        with ui.row().classes("items-center gap-2"):
            provider_chip = ui.chip(
                f"provider: {state['provider']}",
                icon="bolt",
                color="white",
                text_color="primary",
            )

            def toggle_dark() -> None:
                dark.toggle()
                dark_btn.props(
                    f"icon={'light_mode' if dark.value else 'dark_mode'}"
                )

            dark_btn = (
                ui.button(icon="light_mode", on_click=toggle_dark)
                .props("flat round color=white")
                .tooltip("Toggle dark mode")
            )

    # ---------- main split ----------
    with ui.row().classes("w-full no-wrap gap-6 p-6 items-start"):

        # ---------- sidebar ----------
        with ui.column().classes(
            "w-72 shrink-0 gap-4 p-4 rounded-xl"
        ).style(
            "background: rgba(34,197,94,0.06); border: 1px solid rgba(34,197,94,0.18);"
        ):
            ui.label("Model settings").classes(
                "text-sm font-semibold uppercase text-primary"
            )

            ui.select(
                PROVIDERS,
                value=state["provider"],
                label="Provider",
                on_change=on_provider_change,
            ).classes("w-full").props("outlined dense")

            model_input = (
                ui.input(label="Model", value=state["model"])
                .classes("w-full")
                .props("outlined dense")
                .on_value_change(lambda e: state.update(model=e.value))
            )

            api_key_input = (
                ui.input(
                    label=PROVIDER_KEY_LABEL.get(state["provider"], "API Key"),
                    value=state["api_key"],
                    password=True,
                    password_toggle_button=True,
                )
                .classes("w-full")
                .props("outlined dense")
                .on_value_change(lambda e: state.update(api_key=e.value))
            )

            ui.number(
                label="Concurrency",
                value=state["concurrency"],
                min=1,
                max=20,
                step=1,
                on_change=lambda e: state.update(concurrency=int(e.value or 1)),
            ).classes("w-full").props("outlined dense")

            ui.separator()
            ui.label("Tip").classes("text-xs uppercase text-primary")
            ui.label(
                "Changes apply on the next Generate click — current runs keep their settings."
            ).classes("text-xs opacity-70")

        # ---------- main column ----------
        with ui.column().classes("grow gap-4 min-w-0"):

            # --- upload ---
            with ui.card().classes("w-full p-4"):
                ui.label("1. Upload PDF").classes(
                    "text-sm font-semibold text-primary"
                )
                ui.upload(
                    label="Drop a PDF here or click to browse",
                    auto_upload=True,
                    multiple=False,
                    on_upload=on_upload,
                ).props('accept=".pdf" color=primary').classes("w-full")
                upload_status = ui.label("No file selected").classes(
                    "text-xs opacity-50"
                )

            # --- generate / reset / cancel ---
            @ui.refreshable
            def action_buttons() -> None:
                with ui.row().classes("w-full gap-2"):
                    if state["running"] and state["cancel_event"]:
                        ui.button(
                            "Cancel",
                            icon="cancel",
                            on_click=lambda: state["cancel_event"].set(),
                        ).props("color=red unelevated")
                    else:
                        ui.button(
                            "Reset",
                            icon="refresh",
                            on_click=reset_all,
                        ).props("flat color=primary")

            generate_btn = ui.button(
                "Generate Quiz",
                icon="play_arrow",
                on_click=on_generate,
            ).props("color=primary unelevated")
            generate_btn.disable()

            action_buttons()

            # --- progress ---
            progress_view()

            # --- cards ---
            cards_view()


def main() -> None:
    configure_logging()
    app.on_startup(lambda: logger.info("Quizzer UI started"))
    ui.run(
        title="Quizzer",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        dark=True,
        reload=False,
        show=False,
        favicon="🎓",
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
