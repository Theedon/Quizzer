from typing import Literal

from pydantic import BaseModel, Field


class ReviewedQuiz(BaseModel):
    is_relevant: bool = Field(
        ..., description="Whether the quiz is relevant to the content"
    )
    feedback: str = Field(..., description="Feedback on the quiz quality and relevance")


class SingleQuiz(BaseModel):
    question: str = Field(..., description="The quiz question")
    option_a: str = Field(..., description="Answer option A text")
    option_b: str = Field(..., description="Answer option B text")
    option_c: str = Field(..., description="Answer option C text")
    option_d: str = Field(..., description="Answer option D text")
    answer: Literal["A", "B", "C", "D"] = Field(
        ...,
        description="The correct answer option label: A, B, C, or D",
    )
    explanation: str = Field(
        "N/A",
        description="Short explanation for why the correct answer is right",
    )


class MultipleQuiz(BaseModel):
    quizzes: list[SingleQuiz] = Field(
        ..., description="A list of quiz questions with options and answers"
    )
