from pydantic import BaseModel, Field
from typing import Optional, Dict

class LLMDecision(BaseModel):
    """Schema for the structured output expected from the LLM agent decision prompt."""
    action: str = Field(..., description="The primary action the agent decides to take.")
    dialogue: Optional[str] = Field(None, description="Any spoken dialogue or internal monologue.")
    sentiment_shift: float = Field(0.0, description="Shift in the agent's sentiment based on the tick.")
    policy_opinion_shift: Dict[str, float] = Field({}, description="Shift in opinion towards specific policies.")
    spending_ratio_shift: Optional[float] = Field(None, description="Shift in the agent's propensity to spend.")

    class Config:
        # Add example if needed later
        # schema_extra = {
        #     "example": {
        #         "action": "discuss_policy_X",
        #         "dialogue": "I'm really concerned about Policy X, it doesn't seem fair.",
        #         "sentiment_shift": -0.1,
        #         "policy_opinion_shift": {"Policy X": -0.2},
        #         "spending_ratio_shift": -0.05
        #     }
        # }
        pass 