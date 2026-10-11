from pydantic import BaseModel
from typing import Literal

class AIResponse(BaseModel):
    intent: Literal['return', 'cancel_order', 'check_status']
    product: str | None
    reason: str | None

class SummaryResponse(BaseModel):
    intent: Literal['return', 'cancel_order', 'check_status'] | None
    product: str | None
    reason: str | None
    helpful_informations: str | None