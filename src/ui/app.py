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
PROVIDER_KEY_URL = {
    "openai": "https://platform.openai.com/api-keys",
    "google": "https://aistudio.google.com/apikey",
    "groq": "https://console.groq.com/keys",
}

GREEN_PRIMARY = "#16a34a"
GREEN_DARK = "#15803d"
GREEN_ACCENT = "#22c55e"

# Hallmark · genre: playful · macrostructure: Narrative Workflow · theme: Plume
# contrast: pass · nav: app-header · footer: none (tool UI)
HEAD_CSS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root {
  --font-ui: 'Outfit', system-ui, sans-serif;
  --radius-card: 14px;
  --radius-input: 8px;
  --radius-btn:  8px;
  --dur-hover: 160ms;
  --ease-out: cubic-bezier(0.0, 0.0, 0.2, 1.0);
}
.body--dark {
  --color-paper:   oklch(14% 0.008 142);
  --color-paper-2: oklch(19% 0.010 142);
  --color-paper-3: oklch(24% 0.010 142);
  --color-rule:    oklch(30% 0.008 142);
  --color-muted:   oklch(55% 0.008 142);
  --color-ink:     oklch(94% 0.005 100);
  --color-shadow:  oklch(0% 0 0 / 0.45);
}
.body--light {
  --color-paper:   oklch(97% 0.008 142);
  --color-paper-2: oklch(93% 0.010 142);
  --color-paper-3: oklch(89% 0.012 142);
  --color-rule:    oklch(82% 0.008 142);
  --color-muted:   oklch(48% 0.008 142);
  --color-ink:     oklch(18% 0.010 142);
  --color-shadow:  oklch(0% 0 0 / 0.10);
}

/* ── Base ──────────────────────────────────── */
body, .q-app { font-family: var(--font-ui) !important; }

/* ── Page background ───────────────────────── */
.body--dark .q-page-container,
.body--dark .q-page { background: var(--color-paper) !important; }
.body--light .q-page-container,
.body--light .q-page { background: var(--color-paper) !important; }

/* ── Cards ─────────────────────────────────── */
.q-card {
  border-radius: var(--radius-card) !important;
  background: var(--color-paper-2) !important;
  box-shadow: 0 2px 12px -2px var(--color-shadow),
              0 0 0 1px oklch(100% 0 0 / 0.06) !important;
  transition: box-shadow var(--dur-hover) var(--ease-out),
              transform var(--dur-hover) var(--ease-out) !important;
}
.q-card:hover {
  box-shadow: 0 6px 24px -4px var(--color-shadow),
              0 0 0 1px oklch(100% 0 0 / 0.09) !important;
  transform: translateY(-1px) !important;
}

/* ── Header ─────────────────────────────────── */
.body--dark .q-header {
  background: linear-gradient(120deg,
    oklch(30% 0.17 142), oklch(24% 0.12 160)) !important;
  border-bottom: 1px solid oklch(100% 0 0 / 0.08) !important;
  box-shadow: none !important;
}
.body--light .q-header {
  background: linear-gradient(120deg,
    oklch(48% 0.17 142), oklch(40% 0.14 160)) !important;
  border-bottom: 1px solid oklch(0% 0 0 / 0.12) !important;
  box-shadow: none !important;
}

/* ── Drawer ─────────────────────────────────── */
.body--dark .q-drawer {
  background: oklch(16% 0.009 142) !important;
  border-right: 1px solid var(--color-rule) !important;
}
.body--light .q-drawer {
  background: var(--color-paper-2) !important;
  border-right: 1px solid var(--color-rule) !important;
}

/* ── Inputs ─────────────────────────────────── */
.q-field--outlined .q-field__control {
  border-radius: var(--radius-input) !important;
}

/* ── Buttons ────────────────────────────────── */
.q-btn:not(.q-btn--round) {
  border-radius: var(--radius-btn) !important;
  font-family: var(--font-ui) !important;
  font-weight: 600 !important;
}

/* ── Progress bar ───────────────────────────── */
.q-linear-progress { height: 6px !important; border-radius: 999px !important; overflow: hidden !important; }
.q-linear-progress__track, .q-linear-progress__model { border-radius: 999px !important; }

/* ── Upload zone ────────────────────────────── */
.q-uploader { border-radius: var(--radius-card) !important; }
.q-uploader__header { border-radius: var(--radius-card) var(--radius-card) 0 0 !important; }

/* ── Step badge ─────────────────────────────── */
.qz-step-row { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.qz-step-badge {
  display: inline-flex; align-items: center; justify-content: center;
  width: 22px; height: 22px; border-radius: 50%;
  background: var(--q-primary, #16a34a); color: #fff;
  font-size: 11px; font-weight: 800; font-family: var(--font-ui);
  flex-shrink: 0; line-height: 1;
}
.qz-step-label {
  font-size: 11px; font-weight: 700;
  letter-spacing: 0.07em; text-transform: uppercase; opacity: 0.65;
}

/* ── Quiz question prominence ───────────────── */
.qz-question .q-field__native,
.qz-question .q-field__input { font-size: 14px !important; font-weight: 600 !important; line-height: 1.55 !important; }

/* ── Empty state ────────────────────────────── */
.qz-empty {
  display: flex; flex-direction: column; align-items: center;
  gap: 8px; padding: 48px 24px; text-align: center; opacity: 0.5;
}

/* ── Quiz card ──────────────────────────────── */
.qz-q-number {
  display: inline-flex; align-items: center; justify-content: center;
  width: 28px; height: 28px; border-radius: 50%;
  background: var(--q-primary, #16a34a); color: #fff;
  font-size: 11px; font-weight: 800; font-family: var(--font-ui); flex-shrink: 0;
}
.qz-page-chip {
  display: inline-flex; align-items: center;
  padding: 2px 8px; border-radius: 999px;
  font-size: 11px; font-weight: 600; font-family: var(--font-ui);
}
.body--dark .qz-page-chip  { background: oklch(28% 0.010 142); color: oklch(62% 0.010 142); }
.body--light .qz-page-chip { background: oklch(88% 0.012 142); color: oklch(40% 0.010 142); }

.qz-options-label {
  font-size: 10px; font-weight: 700; letter-spacing: 0.08em;
  text-transform: uppercase; font-family: var(--font-ui); margin-bottom: 2px;
}
.body--dark .qz-options-label  { color: oklch(52% 0.008 142); }
.body--light .qz-options-label { color: oklch(45% 0.008 142); }

.qz-option-letter {
  display: inline-flex; align-items: center; justify-content: center;
  width: 26px; height: 26px; border-radius: 7px;
  font-size: 11px; font-weight: 700; font-family: var(--font-ui); flex-shrink: 0;
}
.body--dark .qz-option-letter  { background: oklch(27% 0.010 142); color: oklch(62% 0.010 142); }
.body--light .qz-option-letter { background: oklch(89% 0.012 142); color: oklch(38% 0.010 142); }

.qz-answer-label {
  font-size: 10px; font-weight: 700; letter-spacing: 0.07em;
  text-transform: uppercase; font-family: var(--font-ui);
}
.body--dark .qz-answer-label  { color: oklch(52% 0.008 142); }
.body--light .qz-answer-label { color: oklch(45% 0.008 142); }
</style>
"""


def is_valid_pdf(content: IO[bytes]) -> bool:
    """Check if file content starts with the PDF magic bytes."""
    header = content.read(5)
    content.seek(0)
    return header == b"%PDF-"


def _model_for(provider: str) -> str:
    field = PROVIDER_MODEL_FIELD.get(provider)
    return getattr(settings, field, "") if field else ""


_PHASE_ICON = {
    "idle": "radio_button_unchecked",
    "ingesting": "picture_as_pdf",
    "chunking": "segment",
    "generating": "auto_awesome",
    "aggregating": "check_circle_outline",
    "done": "check_circle",
    "error": "error_outline",
}
_PHASE_TEXT = {
    "idle": "Ready",
    "ingesting": "Reading PDF…",
    "chunking": "Splitting into chunks…",
    "generating": "Generating quiz…",
    "aggregating": "Finalizing…",
    "done": "Done",
    "error": "Generation failed",
}


def _phase_label(p: GenerationProgress) -> str:
    return _PHASE_TEXT.get(p.phase, "Ready")


@ui.page("/")
def index() -> None:
    ui.colors(
        primary=GREEN_PRIMARY,
        secondary=GREEN_DARK,
        accent=GREEN_ACCENT,
        positive=GREEN_PRIMARY,
    )
    dark = ui.dark_mode(value=False)
    ui.add_head_html(HEAD_CSS)

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
            with ui.row().classes("items-center gap-2"):
                ui.icon(_PHASE_ICON.get(p.phase, "radio_button_unchecked")).classes(
                    "text-base text-primary"
                )
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
                token_part = f" · tokens {p.total_tokens:,}" if p.total_tokens else ""
                detail = (
                    f"pages {p.total_pages} · "
                    f"chunks {p.chunks_done}/{p.total_chunks or '?'} · "
                    f"questions {len(p.quizzes)}"
                    f"{token_part}"
                )
            ui.label(detail).classes("text-xs opacity-70")
            if p.phase == "error" and p.error:
                ui.label(f"Error: {p.error}").classes("text-xs text-negative")

    @ui.refreshable
    def cards_view() -> None:
        quizzes: list[dict] = state["quizzes"]
        with ui.row().classes("w-full items-center justify-between"):
            ui.html(
                f'<div class="qz-step-row" style="margin-bottom:0"><span class="qz-step-badge">3</span><span class="qz-step-label">Review &amp; Download ({len(quizzes)})</span></div>'
            )
            download_btn = ui.button(
                "Download CSV",
                icon="download",
                on_click=on_download,
            ).props("color=primary unelevated")
            if not quizzes:
                download_btn.disable()

        if not quizzes:
            with ui.column().classes("qz-empty w-full"):
                ui.icon("auto_stories").classes("text-5xl")
                ui.label("No questions yet").classes("text-sm font-semibold")
                ui.label("Upload a PDF and hit Generate to get started.").classes(
                    "text-xs"
                )
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
                    on_click=lambda: (
                        state.update(page=state["page"] - 1),
                        cards_view.refresh(),
                    ),
                ).props("flat dense round color=primary").bind_enabled_from(
                    state, "page", backward=lambda p: p > 0
                )
                ui.label(f"Page {page + 1} / {total_pages}").classes(
                    "text-xs opacity-70"
                )
                ui.button(
                    icon="chevron_right",
                    on_click=lambda: (
                        state.update(page=state["page"] + 1),
                        cards_view.refresh(),
                    ),
                ).props("flat dense round color=primary").bind_enabled_from(
                    state, "page", backward=lambda p: p < total_pages - 1
                )

    def _quiz_card(idx: int, quiz: dict) -> None:
        with ui.card().classes("w-full p-0"):
            # ── Header ──────────────────────────────
            with ui.row().classes("w-full items-center justify-between px-4 pt-3 pb-2"):
                with ui.row().classes("items-center gap-2"):
                    ui.html(f'<span class="qz-q-number">{idx + 1}</span>')
                    ui.html(
                        f'<span class="qz-page-chip">page {quiz.get("page_number", "?")}</span>'
                    )
                ui.button(
                    icon="delete",
                    on_click=lambda *_, i=idx: delete_quiz(i),
                ).props("flat dense round color=negative").tooltip(
                    "Remove this question"
                )
            ui.separator().style("margin: 0; opacity: 0.15")

            # ── Question + Options + Answer ──────────
            with ui.column().classes("w-full gap-3 px-4 pt-3 pb-3"):
                ui.input(
                    label="Question",
                    value=quiz.get("question", ""),
                ).classes(
                    "w-full qz-question"
                ).props("outlined dense").on_value_change(
                    lambda e, q=quiz: q.update(question=e.value)
                )

                ui.html('<div class="qz-options-label">Options</div>')
                for letter in ("a", "b", "c", "d"):
                    with ui.row().classes("items-center gap-2 w-full"):
                        ui.html(
                            f'<span class="qz-option-letter">{letter.upper()}</span>'
                        )
                        ui.input(
                            value=quiz.get(f"option_{letter}", ""),
                        ).classes(
                            "flex-1"
                        ).props("outlined dense").on_value_change(
                            lambda e, q=quiz, k=f"option_{letter}": q.update(
                                {k: e.value}
                            )
                        )

                ui.separator().style("margin: 2px 0; opacity: 0.10")
                with ui.row().classes("items-center gap-3 flex-wrap"):
                    ui.html('<span class="qz-answer-label">Correct answer</span>')
                    ui.radio(
                        ["A", "B", "C", "D"],
                        value=quiz.get("answer", "A"),
                    ).props("inline dense color=primary").on_value_change(
                        lambda e, q=quiz: q.update(answer=e.value)
                    )

            # ── Explanation (collapsible) ────────────
            ui.separator().style("margin: 0; opacity: 0.10")
            with (
                ui.expansion("Explanation", icon="lightbulb_outline")
                .classes("w-full")
                .props("dense")
            ):
                with ui.column().classes("px-4 pb-3 pt-1 w-full"):
                    ui.textarea(
                        value=quiz.get("explanation", ""),
                    ).classes(
                        "w-full"
                    ).props("outlined dense autogrow").on_value_change(
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
        server_key_map = {
            "openai": settings.OPENAI_API_KEY,
            "google": settings.GEMINI_API_KEY,
            "groq": settings.GROQ_API_KEY,
        }
        if not state["api_key"].strip() and not server_key_map.get(state["provider"]):
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
            ui.notify("Generation in progress — wait for it to finish", type="warning")
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
        for provider, link in key_links.items():
            link.set_visibility(provider == e.value)

    # ============================================================
    # UI build
    # ============================================================

    # ---------- top bar ----------
    with ui.header(elevated=True).classes("items-center justify-between bg-primary"):
        with ui.row().classes("items-center gap-3"):
            ui.button(icon="menu", on_click=lambda: sidebar_drawer.toggle()).props(
                "flat round color=white"
            )
            ui.icon("school").classes("text-2xl text-white")
            ui.label("Quizzer").classes("text-xl font-semibold text-white")
            ui.label("PDF → quiz CSV").classes("text-xs text-white/70 hidden sm:block")
        with ui.row().classes("items-center gap-2"):
            provider_chip = ui.chip(
                f"provider: {state['provider']}",
                icon="bolt",
                color="white",
                text_color="primary",
            )

            def toggle_dark() -> None:
                dark.toggle()
                dark_btn.props(f"icon={'light_mode' if dark.value else 'dark_mode'}")

            dark_btn = (
                ui.button(icon="light_mode", on_click=toggle_dark)
                .props("flat round color=white")
                .tooltip("Toggle dark mode")
            )

    # ---------- sidebar drawer ----------
    with ui.left_drawer(bordered=True).props("breakpoint=768") as sidebar_drawer:
        with ui.column().classes("gap-4 p-4"):
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

            with ui.column().classes("w-full gap-1"):
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

                key_links = {
                    provider: (
                        ui.link(
                            "Get an API key →", PROVIDER_KEY_URL[provider], new_tab=True
                        ).classes("text-xs text-primary")
                    )
                    for provider in PROVIDERS
                }
                for provider, link in key_links.items():
                    link.set_visibility(provider == state["provider"])

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
    with ui.column().classes("w-full gap-4 p-4 sm:p-6"):

        # --- upload ---
        with ui.card().classes("w-full p-4"):
            ui.html(
                '<div class="qz-step-row"><span class="qz-step-badge">1</span><span class="qz-step-label">Upload PDF</span></div>'
            )
            ui.upload(
                label="Drop your PDF here, or click to browse",
                auto_upload=True,
                multiple=False,
                on_upload=on_upload,
            ).props('accept=".pdf" color=primary').classes("w-full")
            upload_status = ui.label("No file selected").classes("text-xs opacity-50")

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

        ui.html(
            '<div class="qz-step-row" style="margin-top:4px"><span class="qz-step-badge">2</span><span class="qz-step-label">Generate</span></div>'
        )
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
        dark=False,
        reload=False,
        show=False,
        favicon="🎓",
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
