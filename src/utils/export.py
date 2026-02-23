import csv
import os
from datetime import datetime
from typing import Any

from src.core.logger import logger


def export_quizzes_to_csv(
    final_quizzes: list, output_dir: str = "outputs", custom_filepath: str | None = None
):
    """
    Exports structured quiz data to a CSV file.
    """
    if not final_quizzes:
        logger.warning("No quizzes to export.")
        return None

    # Determine final filepath
    if custom_filepath:
        filepath = custom_filepath
        # Ensure the directory for custom filepath exists
        custom_dir = os.path.dirname(os.path.abspath(filepath))
        if custom_dir:
            os.makedirs(custom_dir, exist_ok=True)
    else:
        # Fallback to default output directory with timestamped filename
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(output_dir, f"quiz_export_{timestamp}.csv")

    try:
        with open(filepath, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)

            # Write the header row
            writer.writerow(
                [
                    "Question",
                    "Option A",
                    "Option B",
                    "Option C",
                    "Option D",
                    "Correct Answer",
                ]
            )

            # Write data
            logger.warning(f"Exporting --------{(final_quizzes)} quizzes ----")
            for quiz in final_quizzes:
                writer.writerow(
                    [
                        _get_quiz_field(quiz, "question"),
                        _get_quiz_field(quiz, "option_a"),
                        _get_quiz_field(quiz, "option_b"),
                        _get_quiz_field(quiz, "option_c"),
                        _get_quiz_field(quiz, "option_d"),
                        _get_quiz_field(quiz, "answer"),
                    ]
                )

        logger.success(
            f"Successfully exported {len(final_quizzes)} questions to {filepath}"
        )
        return filepath

    except Exception as e:
        logger.exception(f"Failed to export CSV: {e}")
        return None


def _get_quiz_field(quiz: Any, field: str, default: str = "") -> str:
    if isinstance(quiz, dict):
        value = quiz.get(field, default)
    else:
        value = getattr(quiz, field, default)
    return str(value) if value is not None else default
