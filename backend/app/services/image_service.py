from html import escape
from math import cos, pi, sin
from urllib.parse import quote

from app.models import BouquetProposal


FLOWER_COLORS = {
    "粉玫瑰": "#e98aa6",
    "红玫瑰": "#c73542",
    "香槟玫瑰": "#d9b37a",
    "百合": "#f7f2e8",
    "向日葵": "#f2b72e",
    "满天星": "#f8f8f3",
    "尤加利叶": "#7b9b77",
}

FILLER_FLOWERS = {"满天星", "尤加利叶"}


def build_image_prompt(proposal: BouquetProposal) -> str:
    flower_text = ", ".join(
        f"{item.get('quantity', 1)} {item.get('name')}" for item in proposal.flowers
    )
    return (
        "A realistic customized bouquet, "
        f"with {flower_text}, {proposal.packaging}, "
        f"{proposal.style} style, product photography, natural daylight, "
        "clean light background, high detail, elegant floral arrangement."
    )


def mock_image_url(proposal: BouquetProposal) -> str:
    package_color = _packaging_color(proposal.packaging)
    accent_color = _packaging_accent(proposal.packaging)
    flower_shapes = _build_flower_shapes(proposal)
    filler_shapes = _build_filler_shapes(proposal)
    legend_items = _build_legend_items(proposal)

    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="720" height="520" viewBox="0 0 720 520">
      <defs>
        <filter id="softShadow" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="10" stdDeviation="9" flood-color="#8a7a68" flood-opacity="0.18"/>
        </filter>
      </defs>
      <rect width="720" height="520" fill="#f5f1e9"/>
      <rect x="30" y="28" width="660" height="464" rx="22" fill="#fffdf8" stroke="#ddd5c7"/>
      <text x="54" y="72" font-size="24" font-weight="700" fill="#2f4f3f">{escape(proposal.title)}</text>
      <text x="54" y="100" font-size="14" fill="#69746f">Data-driven bouquet preview · 示意图</text>

      <g filter="url(#softShadow)">
        <path d="M216 338 C250 304 418 304 454 338 L401 475 L271 475 Z" fill="{package_color}" stroke="#9b8460" stroke-width="4"/>
        <path d="M238 344 L336 466 L432 344" fill="none" stroke="{accent_color}" stroke-width="9" opacity="0.75"/>
        <path d="M248 336 C280 362 397 363 426 336" fill="none" stroke="#fff7e7" stroke-width="5" opacity="0.9"/>

        <path d="M286 338 C270 260 260 190 246 124" stroke="#6f8f63" stroke-width="7" fill="none"/>
        <path d="M328 338 C326 250 332 178 338 114" stroke="#6f8f63" stroke-width="7" fill="none"/>
        <path d="M376 338 C386 260 405 190 438 124" stroke="#6f8f63" stroke-width="7" fill="none"/>
        <path d="M304 338 C290 278 310 218 292 154" stroke="#6f8f63" stroke-width="6" fill="none"/>
        <path d="M354 338 C356 282 350 214 382 154" stroke="#6f8f63" stroke-width="6" fill="none"/>

        <ellipse cx="257" cy="254" rx="17" ry="48" fill="#86a878" transform="rotate(-38 257 254)"/>
        <ellipse cx="425" cy="255" rx="17" ry="48" fill="#86a878" transform="rotate(38 425 255)"/>
        <ellipse cx="304" cy="282" rx="13" ry="40" fill="#7b9b77" transform="rotate(-18 304 282)"/>
        <ellipse cx="377" cy="282" rx="13" ry="40" fill="#7b9b77" transform="rotate(18 377 282)"/>
        {filler_shapes}
        {flower_shapes}
      </g>

      <rect x="500" y="52" width="152" height="288" rx="14" fill="#f8faf6" stroke="#e1e7dd"/>
      <text x="520" y="84" font-size="17" font-weight="700" fill="#2f4f3f">花材清单</text>
      {legend_items}
      <rect x="500" y="360" width="152" height="82" rx="14" fill="#fff8f1" stroke="#efd9c8"/>
      <text x="520" y="392" font-size="14" fill="#8a4f3a">预计价格</text>
      <text x="520" y="421" font-size="24" font-weight="800" fill="#8a4f3a">{proposal.estimatedPrice} 元</text>
      <text x="54" y="462" font-size="14" fill="#69746f">包装：{escape(proposal.packaging)}</text>
    </svg>
    """
    return "data:image/svg+xml;charset=utf-8," + quote(svg)


def _build_flower_shapes(proposal: BouquetProposal) -> str:
    positions = [
        (336, 152, 1.1),
        (288, 184, 1.0),
        (384, 184, 1.0),
        (248, 238, 0.95),
        (424, 238, 0.95),
        (335, 234, 1.0),
        (292, 288, 0.88),
        (378, 288, 0.88),
        (332, 304, 0.78),
    ]
    primary = []
    for flower in proposal.flowers:
        name = str(flower.get("name", "花材"))
        if name in FILLER_FLOWERS:
            continue
        quantity = int(flower.get("quantity") or 1)
        primary.extend([name] * min(quantity, 5))

    if not primary:
        primary = [str(proposal.flowers[0].get("name", "花材"))] if proposal.flowers else ["花材"]

    shapes = []
    for index, name in enumerate(primary[: len(positions)]):
        x, y, scale = positions[index]
        shapes.append(_flower_svg(x, y, FLOWER_COLORS.get(name, "#d99ca8"), scale))
    return "".join(shapes)


def _build_filler_shapes(proposal: BouquetProposal) -> str:
    dots = []
    has_babys_breath = any(str(item.get("name")) == "满天星" for item in proposal.flowers)
    if has_babys_breath:
        for index in range(24):
            angle = index * (pi / 12)
            radius = 96 + (index % 4) * 16
            x = 336 + cos(angle) * radius
            y = 228 + sin(angle) * radius * 0.72
            dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="#fffdf7" stroke="#d7d2c8" stroke-width="1"/>')
    return "".join(dots)


def _build_legend_items(proposal: BouquetProposal) -> str:
    rows = []
    for index, flower in enumerate(proposal.flowers[:6]):
        name = str(flower.get("name", "花材"))
        color = FLOWER_COLORS.get(name, "#d99ca8")
        rows.append(
            f"""
            <g transform="translate(520 {118 + index * 34})">
              <circle cx="0" cy="0" r="8" fill="{color}" stroke="#ffffff" stroke-width="2"/>
              <text x="18" y="5" font-size="14" fill="#425047">{escape(name)} x {flower.get("quantity")}</text>
            </g>
            """
        )
    return "".join(rows)


def _flower_svg(x: int, y: int, color: str, scale: float) -> str:
    stroke = "#8f6c5f" if color == "#f7f2e8" else "#ffffff"
    r = 20 * scale
    center = 10 * scale
    offset = 15 * scale
    return f"""
    <g>
      <circle cx="{x - offset:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{color}" stroke="{stroke}" stroke-width="3"/>
      <circle cx="{x + offset:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{color}" stroke="{stroke}" stroke-width="3"/>
      <circle cx="{x:.1f}" cy="{y - offset:.1f}" r="{r:.1f}" fill="{color}" stroke="{stroke}" stroke-width="3"/>
      <circle cx="{x:.1f}" cy="{y + offset:.1f}" r="{r:.1f}" fill="{color}" stroke="{stroke}" stroke-width="3"/>
      <circle cx="{x:.1f}" cy="{y:.1f}" r="{center:.1f}" fill="#f7d78a" stroke="#fff6d2" stroke-width="2"/>
    </g>
    """


def _packaging_color(packaging: str) -> str:
    if "粉" in packaging:
        return "#e7b6c4"
    if "白" in packaging:
        return "#f2efe8"
    if "香槟" in packaging or "高级" in packaging:
        return "#d9c7a2"
    return "#d2c3b3"


def _packaging_accent(packaging: str) -> str:
    if "粉" in packaging:
        return "#fff0f5"
    if "白" in packaging:
        return "#ffffff"
    if "香槟" in packaging or "高级" in packaging:
        return "#fff5dd"
    return "#f7eadc"

