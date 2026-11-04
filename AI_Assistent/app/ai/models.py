from pydantic import BaseModel
from typing import Literal

class AIResponse(BaseModel):
    intent: Literal['return', 'cancel_order', 'check_status'] | None
    product: str | None
    reason: str | None
    response_to_client: str | None
    response_supported_by_documentation: bool

class SummaryResponse(BaseModel):
    intent: Literal['return', 'cancel_order', 'check_status'] | None
    product: str | None
    reason: str | None
    helpful_informations: list[str] | None