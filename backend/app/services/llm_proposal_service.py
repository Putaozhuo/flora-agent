import json

from app.models import BouquetProposal, BouquetRequirement, InventoryCheckItem
from app.services.inventory_service import find_item
from app.services.llm_parser_service import _get_api_key, _get_base_url, _get_model


def build_proposal_with_llm(
    requirement: BouquetRequirement,
    inventory_check: list[InventoryCheckItem],
    fallback_proposal: BouquetProposal,
) -> tuple[BouquetProposal, bool]:
    if not _get_api_key():
        return fallback_proposal, False

    try:
        from openai import OpenAI

        client_kwargs = {"api_key": _get_api_key()}
        base_url = _get_base_url()
        if base_url:
            client_kwargs["base_url"] = base_url

        response = OpenAI(**client_kwargs).chat.completions.create(
            model=_get_model(),
            messages=_build_messages(requirement, inventory_check, fallback_proposal),
            response_format={"type": "json_object"},
            temperature=0.5,
            max_tokens=900,
        )
        content = response.choices[0].message.content
        if not content:
            return fallback_proposal

        data = json.loads(content)
        return BouquetProposal(
            title=str(data.get("title") or fallback_proposal.title),
            flowers=fallback_proposal.flowers,
            packaging=fallback_proposal.packaging,
            style=str(data.get("style") or fallback_proposal.style),
            meaning=str(data.get("meaning") or fallback_proposal.meaning),
            estimatedPrice=fallback_proposal.estimatedPrice,
            notes=_merge_notes(fallback_proposal.notes, data.get("notes")),
        ), True
    except Exception:
        return fallback_proposal, False


def _build_messages(
    requirement: BouquetRequirement,
    inventory_check: list[InventoryCheckItem],
    fallback_proposal: BouquetProposal,
) -> list[dict[str, str]]:
    flower_meanings = []
    for flower in fallback_proposal.flowers:
        item = find_item(str(flower.get("name")))
        if item:
            flower_meanings.append({"name": item.name, "meaning": item.meaning})

    payload = {
        "requirement": requirement.model_dump(),
        "inventory_check": [item.model_dump() for item in inventory_check],
        "locked_plan": {
            "flowers": fallback_proposal.flowers,
            "packaging": fallback_proposal.packaging,
            "estimatedPrice": fallback_proposal.estimatedPrice,
            "notes": fallback_proposal.notes,
        },
        "flower_meanings": flower_meanings,
    }

    return [
        {
            "role": "system",
            "content": (
                "You are a florist design copywriter for a bouquet customization agent. "
                "Return JSON only. Use Chinese. "
                "You may polish title, style, meaning, and notes. "
                "Do not change flowers, quantities, packaging, or estimatedPrice. "
                "Output fields: title, style, meaning, notes. "
                "notes must be an array of short Chinese strings."
            ),
        },
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]


def _merge_notes(fallback_notes: list[str], llm_notes: object) -> list[str]:
    notes = list(fallback_notes)
    if isinstance(llm_notes, list):
        for note in llm_notes:
            if isinstance(note, str) and note not in notes:
                notes.append(note)
    return notes
