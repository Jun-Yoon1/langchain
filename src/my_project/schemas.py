from typing import List

from pydantic import BaseModel, Field


class GitHubRepo(BaseModel):
    name: str
    url: str
    stars: int
    description: str = ""


class PipelineRecommendation(BaseModel):
    recommended_level: str = Field(description="Level 1 / Level 2 / Level 3")
    reason: str = Field(description="추천 이유 (강의 자료 근거 포함)")
    components: List[str] = Field(description="필요한 파일 목록 예: loader.py, retriever.py")
    lecture_sections: List[str] = Field(description="복습할 강의 섹션 예: ['S1', 'S2']")
    github_refs: List[GitHubRepo] = Field(description="참고 GitHub 레포 목록")
