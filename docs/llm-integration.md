# LLM 结构化解析接入说明

当前项目支持 OpenAI 兼容接口。后端会优先调用真实 LLM，把用户自然语言解析成 `BouquetRequirement`；如果没有配置 API key 或调用失败，会自动回退到本地规则解析。

## 推荐配置：硅基流动 SiliconFlow 的 DeepSeek

在 `backend/.env` 中填写：

```text
LLM_API_KEY=你的硅基流动 API Key
LLM_BASE_URL=https://api.siliconflow.cn/v1
LLM_MODEL=deepseek-ai/DeepSeek-V3
```

配置后重启后端。如果调用成功，前端解析方式会显示为 `LLM 结构化解析`。

## OpenAI 配置

如果之后要换回 OpenAI，可以改成：

```text
OPENAI_API_KEY=你的 OpenAI API Key
OPENAI_MODEL=gpt-4o-mini
```

## 当前解析链路

1. 用户输入自然语言需求。
2. 后端读取 `.env` 中的模型配置。
3. 有可用 key 时调用 LLM 输出需求 JSON。
4. 无 key 或调用失败时使用规则解析兜底。
5. LangGraph 根据解析结果决定追问、查库存或生成方案。
6. 方案生成阶段先由后端工具锁定花材、数量、包装和价格，再让 LLM 润色标题、风格说明、花语解释和备注。
