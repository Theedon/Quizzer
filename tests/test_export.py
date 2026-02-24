from pathlib import Path

from src.utils.export import export_quizzes_to_csv


def test_export_quizzes_to_csv_with_dict_rows(tmp_path: Path) -> None:
    output_path = tmp_path / "quiz.csv"
    quizzes = [
        {
            "question": "What is 2 + 2?",
            "option_a": "3",
            "option_b": "4",
            "option_c": "5",
            "option_d": "6",
            "answer": "B",
        }
    ]

    filepath = export_quizzes_to_csv(quizzes, custom_filepath=str(output_path))

    assert filepath == str(output_path)
    assert output_path.exists()

    csv_content = output_path.read_text(encoding="utf-8")
    assert (
        "Question,Option A,Option B,Option C,Option D,Correct Answer,Explanation"
        in csv_content
    )
    assert "What is 2 + 2?,3,4,5,6,B,N/A" in csv_content
