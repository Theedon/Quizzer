from src.agent.schemas import (
    MultipleQuiz,
    SingleQuiz,
)


def test_single_quiz_schema_has_explicit_option_fields() -> None:
    schema = SingleQuiz.model_json_schema()

    assert set(schema["properties"].keys()) == {
        "question",
        "option_a",
        "option_b",
        "option_c",
        "option_d",
        "answer",
    }
    assert set(schema["required"]) == {
        "question",
        "option_a",
        "option_b",
        "option_c",
        "option_d",
        "answer",
    }


def test_multiple_quiz_wraps_single_quiz_list() -> None:
    schema = MultipleQuiz.model_json_schema()

    assert "quizzes" in schema["properties"]
    quizzes_schema = schema["properties"]["quizzes"]
    assert quizzes_schema["type"] == "array"
    assert "$ref" in quizzes_schema["items"]
