import type { AgentMessageResponse, InventoryItem } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export async function fetchInventory(): Promise<InventoryItem[]> {
  const response = await fetch(`${API_BASE}/inventory`);
  if (!response.ok) {
    throw new Error("库存接口请求失败");
  }
  return response.json();
}

export async function sendAgentMessage(
  message: string,
  sessionId?: string,
): Promise<AgentMessageResponse> {
  const response = await fetch(`${API_BASE}/agent/message`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ message, sessionId }),
  });
  if (!response.ok) {
    throw new Error("Agent 接口请求失败");
  }
  return response.json();
}

