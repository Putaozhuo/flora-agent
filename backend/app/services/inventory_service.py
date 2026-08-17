import json
from pathlib import Path

from app.models import FlowerRequest, InventoryCheckItem, InventoryItem


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "inventory.json"


def load_inventory() -> list[InventoryItem]:
    raw_items = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return [InventoryItem(**item) for item in raw_items]


def find_item(name: str) -> InventoryItem | None:
    for item in load_inventory():
        if item.name == name:
            return item
    return None


def recommend_substitute(target_name: str, preferred_style: str | None = None) -> str | None:
    target = find_item(target_name)
    inventory = load_inventory()
    candidates = [item for item in inventory if item.name != target_name and item.stock > 0]
    if not candidates:
        return None

    if target:
        for candidate in candidates:
            if set(candidate.styles).intersection(target.styles) or set(candidate.colors).intersection(target.colors):
                return candidate.name

    if preferred_style:
        for candidate in candidates:
            if any(style in preferred_style for style in candidate.styles):
                return candidate.name

    return candidates[0].name


def check_inventory(flowers: list[FlowerRequest], preferred_style: str | None = None) -> list[InventoryCheckItem]:
    results: list[InventoryCheckItem] = []
    for flower in flowers:
        requested = flower.quantity or 1
        item = find_item(flower.name)
        if not item:
            results.append(
                InventoryCheckItem(
                    name=flower.name,
                    requested=requested,
                    available=0,
                    enough=False,
                    substitute=recommend_substitute(flower.name, preferred_style),
                    note="当前库存中没有该花材。",
                )
            )
            continue

        enough = item.stock >= requested
        results.append(
            InventoryCheckItem(
                name=item.name,
                requested=requested,
                available=item.stock,
                enough=enough,
                unitPrice=item.unitPrice,
                substitute=None if enough else recommend_substitute(item.name, preferred_style),
                note=None if enough else "库存数量不足，建议使用替代花材或减少数量。",
            )
        )
    return results

