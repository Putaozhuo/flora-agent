# MVP 接口设计

## GET `/health`

健康检查。

响应：

```json
{
  "status": "ok",
  "service": "flora-agent"
}
```

## GET `/inventory`

查询当前模拟库存。

响应：

```json
[
  {
    "name": "粉玫瑰",
    "stock": 12,
    "unitPrice": 12,
    "meaning": "温柔、浪漫、喜欢"
  }
]
```

## POST `/agent/message`

发送用户消息并推进 Agent 工作流。

请求：

```json
{
  "sessionId": "optional-session-id",
  "message": "我想送女朋友一束花，预算 200 元"
}
```

响应：

```json
{
  "sessionId": "generated-session-id",
  "stage": "waiting_confirmation",
  "parserMode": "rule_based",
  "reply": "我已经为你生成了一版方案...",
  "requirement": {},
  "inventoryCheck": [],
  "proposal": {},
  "imagePrompt": "",
  "imageUrl": "",
  "orderDraft": null,
  "nextActions": ["confirm", "revise"]
}
```

## 工作流阶段

- `collecting_requirements`：收集需求
- `clarifying`：追问缺失信息
- `checking_inventory`：校验库存
- `generating_proposal`：生成方案
- `waiting_confirmation`：等待用户确认或修改
- `confirmed`：已生成商家制作单

## LangGraph 工作流节点

第一版后端使用 LangGraph 编排核心 Agent 流程：

- `validate_requirements`：检查用户需求是否足够
- `clarify_requirements`：生成追问回复
- `check_inventory`：调用库存校验工具
- `generate_proposal`：生成花束方案、图片 Prompt 和 mock 效果图

用户确认属于 human-in-the-loop 节点：系统停在 `waiting_confirmation`，等待用户输入“确认”“满意”或继续修改需求。后续接入真实 LangGraph checkpointer 后，可以把会话状态持久化到 SQLite 或 PostgreSQL。

## LLM 解析模式

响应里的 `parserMode` 表示本轮需求解析来源：

- `llm`：使用 OpenAI Structured Outputs 完成结构化解析
- `rule_based`：没有 API key、LLM 调用失败或本地演示时，使用规则解析兜底
