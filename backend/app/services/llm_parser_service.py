import json
import os

from app.models import BouquetRequirement

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


REQUIREMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "recipient": {
            "type": ["string", "null"],
            "description": "Gift recipient, such as girlfriend, friend, mother, teacher. Null if missing.",
        },
        "occasion": {
            "type": ["string", "null"],
            "description": "Occasion, such as birthday, anniversary, confession, graduation. Null if missing.",
        },
        "budget": {
            "type": ["integer", "null"],
            "description": "Budget amount in CNY. Null if missing.",
        },
        "style": {
            "type": ["string", "null"],
            "description": "Bouquet style in Chinese short phrases, such as 温柔、高级、浪漫.",
        },
        "flowers": {
            "type": "array",
            "description": "Flowers explicitly mentioned by the user.",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "quantity": {"type": ["integer", "null"]},
                },
                "required": ["name", "quantity"],
                "additionalProperties": False,
            },
        },
        "packaging": {
            "type": ["string", "null"],
            "description": "Packaging preference in Chinese. Null if missing.",
        },
        "constraints": {
            "type": "array",
            "description": "Special constraints, dislikes, taboos, or must-have requirements.",
            "items": {"type": "string"},
        },
    },
    "required": ["recipient", "occasion", "budget", "style", "flowers", "packaging", "constraints"],
    "additionalProperties": False,
}


def parse_requirement_with_llm(message: str) -> BouquetRequirement | None:
    api_key = _get_api_key()
    if not api_key:
        return None

    try:
        from openai import OpenAI

        client_kwargs = {"api_key": api_key}
        base_url = _get_base_url()
        if base_url:
            client_kwargs["base_url"] = base_url

        client = OpenAI(**client_kwargs)
        response = client.chat.completions.create(
            model=_get_model(),
            messages=_build_messages(message),
            response_format=_get_response_format(),
            temperature=0.1,
            max_tokens=800,
        )
        content = response.choices[0].message.content
        if not content:
            return None
        return BouquetRequirement(**json.loads(content))
    except Exception:
        return None


def _get_api_key() -> str | None:
    return (
        os.getenv("LLM_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("DEEPSEEK_API_KEY")
        or os.getenv("SILICONFLOW_API_KEY")
        or os.getenv("DASHSCOPE_API_KEY")
    )


def _get_base_url() -> str | None:
    return os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL")


def _get_model() -> str:
    return os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"


def _get_response_format() -> dict:
    if _get_base_url():
        return {"type": "json_object"}
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "bouquet_requirement",
            "schema": REQUIREMENT_SCHEMA,
            "strict": True,
        },
    }


def _build_messages(message: str) -> list[dict[str, str]]:
    schema_example = json.dumps(
        {
            "recipient": "女朋友",
            "occasion": None,
            "budget": 200,
            "style": "温柔、高级",
            "flowers": [{"name": "粉玫瑰", "quantity": 6}],
            "packaging": "香槟色高级包装纸",
            "constraints": [],
        },
        ensure_ascii=False,
    )
    return [
        {
            "role": "system",
            "content": (
                "你是鲜花定制 Agent 的需求解析器。"
                "请只输出 JSON，不要输出解释。"
                "只提取用户明确表达或强烈暗示的信息，不要编造库存、价格或花材数量。"
                "如果信息缺失，字段填 null 或空数组。"
                "JSON 字段必须是 recipient, occasion, budget, style, flowers, packaging, constraints。"
                f"JSON 示例：{schema_example}"
            ),
        },
        {"role": "user", "content": message},
    ]
