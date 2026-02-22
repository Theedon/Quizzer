from pydantic import BaseModel, Field


class ReviewedQuiz(BaseModel):
    is_relevant: bool = Field(
        ..., description="Whether the quiz is relevant to the content"
    )
    feedback: str = Field(..., description="Feedback on the quiz quality and relevance")


class SingleQuiz(BaseModel):
    question: str = Field(..., description="The quiz question")
    options: dict[str, str] = Field(
        ...,
        description="The answer options for the quiz, they should be 4 options with one correct answer and three distractors, in the form {'A': 'option text', 'B': 'option text', 'C': 'option text', 'D': 'option text'}",
    )
    answer: str = Field(
        ...,
        description="The correct answer option for the quiz e.g. 'A', 'B', 'C', or 'D'",
    )


class MultipleQuiz(BaseModel):
    quizzes: list[SingleQuiz] = Field(
        ..., description="A list of quiz questions with options and answers"
    )
