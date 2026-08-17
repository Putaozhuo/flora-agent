import { ClipboardCheck, Flower2, PackageCheck, Send, Sparkles } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { fetchInventory, sendAgentMessage } from "./api";
import type { AgentMessageResponse, InventoryItem } from "./types";

interface ChatMessage {
  role: "user" | "agent";
  content: string;
}

const EXAMPLE =
  "我想送女朋友一束温柔一点的花，预算 200 元，想要 6 枝粉玫瑰，加一点满天星，包装高级一点。";

const STAGE_LABELS: Record<string, string> = {
  collecting_requirements: "收集需求",
  clarifying: "追问信息",
  checking_inventory: "校验库存",
  generating_proposal: "生成方案",
  waiting_confirmation: "等待确认",
  confirmed: "已生成制作单",
};

function App() {
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "agent",
      content: "你好，我是 FloraAgent。告诉我你想送给谁、预算、喜欢的花材或风格，我会帮你生成一束可制作的定制花束。",
    },
  ]);
  const [input, setInput] = useState(EXAMPLE);
  const [sessionId, setSessionId] = useState<string>();
  const [agentState, setAgentState] = useState<AgentMessageResponse>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>();

  useEffect(() => {
    fetchInventory()
      .then(setInventory)
      .catch(() => setError("库存数据加载失败，请确认后端服务已启动。"));
  }, []);

  const stageLabel = useMemo(() => {
    if (!agentState) return "待开始";
    return STAGE_LABELS[agentState.stage] ?? agentState.stage;
  }, [agentState]);

  async function handleSend(text = input) {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    setLoading(true);
    setError(undefined);
    setInput("");
    setMessages((current) => [...current, { role: "user", content: trimmed }]);

    try {
      const response = await sendAgentMessage(trimmed, sessionId);
      setSessionId(response.sessionId);
      setAgentState(response);
      setMessages((current) => [...current, { role: "agent", content: response.reply }]);
    } catch {
      setError("请求失败，请确认后端服务已启动。");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="app-shell">
      <section className="workspace">
        <aside className="sidebar">
          <div className="brand">
            <Flower2 aria-hidden="true" />
            <div>
              <h1>FloraAgent</h1>
              <p>定制花束智能体工作流</p>
            </div>
          </div>

          <div className="status-card">
            <span>当前阶段</span>
            <strong>{stageLabel}</strong>
          </div>

          <section className="panel trace-panel">
            <div className="panel-title">
              <Sparkles aria-hidden="true" />
              <h2>Agent Trace</h2>
            </div>
            <div className="trace-meta">
              <span>Model</span>
              <strong>{agentState?.llmModel ?? "Not called yet"}</strong>
            </div>
            <div className="trace-list">
              {agentState?.trace.length ? (
                agentState.trace.map((event, index) => (
                  <article className={`trace-item ${event.status}`} key={`${event.node}-${index}`}>
                    <div>
                      <strong>{event.node}</strong>
                      <span>{event.type} / {event.status}</span>
                    </div>
                    <p>{event.detail}</p>
                  </article>
                ))
              ) : (
                <p className="empty-text">发送需求后展示本轮 Agent 执行轨迹。</p>
              )}
            </div>
          </section>

          <section className="panel inventory-panel">
            <div className="panel-title">
              <PackageCheck aria-hidden="true" />
              <h2>商家库存</h2>
            </div>
            <div className="inventory-list">
              {inventory.map((item) => (
                <article className="inventory-item" key={item.name}>
                  <div>
                    <strong>{item.name}</strong>
                    <span>{item.meaning}</span>
                  </div>
                  <em>{item.stock} 件</em>
                </article>
              ))}
            </div>
          </section>
        </aside>

        <section className="main-panel">
          <div className="chat-panel">
            <div className="chat-header">
              <div>
                <h2>需求对话</h2>
                <p>Agent 会解析需求、检查库存并生成可制作方案。</p>
              </div>
              <button className="ghost-button" onClick={() => handleSend(EXAMPLE)} disabled={loading}>
                <Sparkles size={16} />
                示例
              </button>
            </div>

            <div className="messages">
              {messages.map((message, index) => (
                <div className={`message ${message.role}`} key={`${message.role}-${index}`}>
                  {message.content}
                </div>
              ))}
            </div>

            <div className="composer">
              <textarea
                value={input}
                onChange={(event) => setInput(event.target.value)}
                placeholder="输入你的定制花束需求..."
              />
              <button aria-label="发送需求" onClick={() => handleSend()} disabled={loading}>
                <Send size={18} />
              </button>
            </div>
            {agentState?.stage === "waiting_confirmation" && (
              <div className="action-row">
                {agentState.nextActions.includes("confirm") && (
                  <button className="primary-action" onClick={() => handleSend("确认下单")} disabled={loading}>
                    <ClipboardCheck size={16} />
                    确认下单
                  </button>
                )}
                {agentState.nextActions.includes("revise") && (
                  <button
                    className="secondary-action"
                    onClick={() => setInput("我想把包装改得更高级一点，整体颜色不要太粉。")}
                    disabled={loading}
                  >
                    填写修改意见
                  </button>
                )}
              </div>
            )}
            {error && <p className="error-text">{error}</p>}
          </div>

          <div className="result-grid">
            <section className="panel">
              <div className="panel-title">
                <Sparkles aria-hidden="true" />
                <h2>解析结果</h2>
              </div>
              <dl className="kv-list">
                <div>
                  <dt>解析方式</dt>
                  <dd>{agentState?.parserMode === "llm" ? "LLM 结构化解析" : "规则解析兜底"}</dd>
                </div>
                <div>
                  <dt>对象/场景</dt>
                  <dd>{agentState?.requirement.recipient ?? agentState?.requirement.occasion ?? "待补充"}</dd>
                </div>
                <div>
                  <dt>预算</dt>
                  <dd>{agentState?.requirement.budget ? `${agentState.requirement.budget} 元` : "待补充"}</dd>
                </div>
                <div>
                  <dt>风格</dt>
                  <dd>{agentState?.requirement.style ?? "待补充"}</dd>
                </div>
                <div>
                  <dt>花材</dt>
                  <dd>
                    {agentState?.requirement.flowers.length
                      ? agentState.requirement.flowers.map((flower) => `${flower.name} ${flower.quantity ?? "待定"}`).join("、")
                      : "待补充"}
                  </dd>
                </div>
              </dl>
            </section>

            <section className="panel">
              <div className="panel-title">
                <ClipboardCheck aria-hidden="true" />
                <h2>库存校验</h2>
              </div>
              <div className="check-list">
                {agentState?.inventoryCheck.length ? (
                  agentState.inventoryCheck.map((item) => (
                    <article className={item.enough ? "check-item ok" : "check-item warn"} key={item.name}>
                      <strong>{item.name}</strong>
                      <span>
                        需要 {item.requested}，库存 {item.available}
                      </span>
                      {item.note && <small>{item.note}</small>}
                      {item.substitute && <small>建议替代：{item.substitute}</small>}
                    </article>
                  ))
                ) : (
                  <p className="empty-text">完成需求解析后会自动校验库存。</p>
                )}
              </div>
            </section>
          </div>
        </section>

        <aside className="preview-panel">
          <section className="panel proposal-panel">
            <div className="panel-title">
              <Flower2 aria-hidden="true" />
              <h2>花束方案</h2>
            </div>
            {agentState?.proposal ? (
              <>
                <h3>{agentState.proposal.title}</h3>
                <p>{agentState.proposal.meaning}</p>
                <ul>
                  {agentState.proposal.flowers.map((flower, index) => (
                    <li key={`${flower.name}-${index}`}>{flower.name} x {flower.quantity}</li>
                  ))}
                </ul>
                <div className="price">预计 {agentState.proposal.estimatedPrice} 元</div>
              </>
            ) : (
              <p className="empty-text">方案生成后会显示在这里。</p>
            )}
          </section>

          <section className="image-preview">
            {agentState?.imageUrl ? (
              <img src={agentState.imageUrl} alt="花束效果图" />
            ) : (
              <div className="image-placeholder">效果图预览</div>
            )}
          </section>

          <section className="panel order-panel">
            <div className="panel-title">
              <ClipboardCheck aria-hidden="true" />
              <h2>商家制作单</h2>
            </div>
            {agentState?.orderDraft ? (
              <>
                <p>{agentState.orderDraft.merchantNote}</p>
                <strong>{agentState.orderDraft.estimatedPrice} 元</strong>
              </>
            ) : (
              <p className="empty-text">用户确认满意后生成。</p>
            )}
          </section>
        </aside>
      </section>
    </main>
  );
}

export default App;
