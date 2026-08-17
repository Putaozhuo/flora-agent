from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models import AgentMessageRequest, AgentMessageResponse, InventoryItem
from app.services.agent_workflow import handle_message
from app.services.inventory_service import load_inventory


app = FastAPI(title="FloraAgent API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "flora-agent"}


@app.get("/inventory", response_model=list[InventoryItem])
def inventory() -> list[InventoryItem]:
    return load_inventory()


@app.post("/agent/message", response_model=AgentMessageResponse)
def agent_message(payload: AgentMessageRequest) -> AgentMessageResponse:
    return handle_message(payload.sessionId, payload.message.strip())

