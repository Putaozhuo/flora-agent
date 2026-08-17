from typing import Any, Literal

from pydantic import BaseModel, Field


Stage = Literal[
    "collecting_requirements",
    "clarifying",
    "checking_inventory",
    "generating_proposal",
    "waiting_confirmation",
    "confirmed",
]

ParserMode = Literal["llm", "rule_based"]
TraceType = Literal["llm", "tool", "control", "human"]
TraceStatus = Literal["success", "fallback", "waiting", "skipped"]


class AgentMessageRequest(BaseModel):
    sessionId: str | None = None
    message: str = Field(min_length=1)


class FlowerRequest(BaseModel):
    name: str
    quantity: int | None = None


class BouquetRequirement(BaseModel):
    recipient: str | None = None
    occasion: str | None = None
    budget: int | None = None
    style: str | None = None
    flowers: list[FlowerRequest] = Field(default_factory=list)
    packaging: str | None = None
    constraints: list[str] = Field(default_factory=list)


class InventoryItem(BaseModel):
    name: str
    stock: int
    unitPrice: int
    meaning: str
    colors: list[str] = Field(default_factory=list)
    styles: list[str] = Field(default_factory=list)


class InventoryCheckItem(BaseModel):
    name: str
    requested: int
    available: int
    enough: bool
    unitPrice: int | None = None
    substitute: str | None = None
    note: str | None = None


class BouquetProposal(BaseModel):
    title: str
    flowers: list[dict[str, Any]]
    packaging: str
    style: str
    meaning: str
    estimatedPrice: int
    notes: list[str] = Field(default_factory=list)


class OrderDraft(BaseModel):
    orderStatus: str = "draft_confirmed"
    flowers: list[dict[str, Any]]
    packaging: str
    style: str
    estimatedPrice: int
    merchantNote: str
    imageUrl: str | None = None


class TraceEvent(BaseModel):
    node: str
    type: TraceType
    status: TraceStatus
    detail: str


class AgentMessageResponse(BaseModel):
    sessionId: str
    stage: Stage
    parserMode: ParserMode = "rule_based"
    llmModel: str | None = None
    trace: list[TraceEvent] = Field(default_factory=list)
    reply: str
    requirement: BouquetRequirement
    inventoryCheck: list[InventoryCheckItem] = Field(default_factory=list)
    proposal: BouquetProposal | None = None
    imagePrompt: str | None = None
    imageUrl: str | None = None
    orderDraft: OrderDraft | None = None
    nextActions: list[str] = Field(default_factory=list)
