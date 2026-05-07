from pydantic import BaseModel, Field


class Query(BaseModel):
    question: str = Field(..., description="User question")


class Answer(BaseModel):
    answer: str = Field(..., description="Generated answer")
    sources: list[str] = Field(default_factory=list, description="Referenced source paths")
