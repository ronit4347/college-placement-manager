from pydantic import BaseModel, ConfigDict


class EligibilityResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    eligible: bool
    reasons: list[str]
