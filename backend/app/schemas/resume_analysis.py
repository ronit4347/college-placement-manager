from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MatchDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["MATCH", "PARTIAL", "NOT_FOUND"]
    explanation: str = Field(max_length=600)


class ResumeAnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    overall_match_percentage: int = Field(ge=0, le=100)
    matching_skills: list[str] = Field(max_length=50)
    missing_skills: list[str] = Field(max_length=50)
    education_match: MatchDetail
    experience_match: MatchDetail
    improvement_suggestions: list[str] = Field(min_length=1, max_length=8)
    analysis_mode: Literal["MOCK", "AI"]

    @model_validator(mode="after")
    def skills_are_unique_and_disjoint(self):
        matching = {skill.casefold() for skill in self.matching_skills}
        missing = {skill.casefold() for skill in self.missing_skills}
        if len(matching) != len(self.matching_skills) or len(missing) != len(self.missing_skills):
            raise ValueError("Skill lists must not contain duplicates.")
        if matching & missing:
            raise ValueError("A skill cannot be both matching and missing.")
        return self


class ResumeAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    job_drive_id: int = Field(gt=0)
