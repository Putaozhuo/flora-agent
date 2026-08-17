export type Stage =
  | "collecting_requirements"
  | "clarifying"
  | "checking_inventory"
  | "generating_proposal"
  | "waiting_confirmation"
  | "confirmed";

export interface FlowerRequest {
  name: string;
  quantity?: number | null;
}

export interface BouquetRequirement {
  recipient?: string | null;
  occasion?: string | null;
  budget?: number | null;
  style?: string | null;
  flowers: FlowerRequest[];
  packaging?: string | null;
  constraints: string[];
}

export interface InventoryItem {
  name: string;
  stock: number;
  unitPrice: number;
  meaning: string;
  colors: string[];
  styles: string[];
}

export interface InventoryCheckItem {
  name: string;
  requested: number;
  available: number;
  enough: boolean;
  unitPrice?: number | null;
  substitute?: string | null;
  note?: string | null;
}

export interface BouquetProposal {
  title: string;
  flowers: Array<Record<string, string | number | null>>;
  packaging: string;
  style: string;
  meaning: string;
  estimatedPrice: number;
  notes: string[];
}

export interface OrderDraft {
  orderStatus: string;
  flowers: Array<Record<string, string | number | null>>;
  packaging: string;
  style: string;
  estimatedPrice: number;
  merchantNote: string;
  imageUrl?: string | null;
}

export interface TraceEvent {
  node: string;
  type: "llm" | "tool" | "control" | "human";
  status: "success" | "fallback" | "waiting" | "skipped";
  detail: string;
}

export interface AgentMessageResponse {
  sessionId: string;
  stage: Stage;
  parserMode: "llm" | "rule_based";
  llmModel?: string | null;
  trace: TraceEvent[];
  reply: string;
  requirement: BouquetRequirement;
  inventoryCheck: InventoryCheckItem[];
  proposal?: BouquetProposal | null;
  imagePrompt?: string | null;
  imageUrl?: string | null;
  orderDraft?: OrderDraft | null;
  nextActions: string[];
}
