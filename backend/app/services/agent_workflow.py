import re
import uuid
from copy import deepcopy
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from app.models import (
    AgentMessageResponse,
    BouquetProposal,
    BouquetRequirement,
    FlowerRequest,
    InventoryCheckItem,
    OrderDraft,
    ParserMode,
)
from app.services.image_service import build_image_prompt, mock_image_url
from app.services.inventory_service import check_inventory, find_item
from app.services.llm_parser_service import _get_model, parse_requirement_with_llm
from app.services.llm_proposal_service import build_proposal_with_llm


SessionState = dict[str, Any]


class WorkflowState(TypedDict):
    session: SessionState
    route: Literal["clarify", "generate"]


SESSIONS: dict[str, SessionState] = {}

KNOWN_FLOWERS = ["粉玫瑰", "红玫瑰", "香槟玫瑰", "百合", "向日葵", "满天星", "尤加利叶"]
RECIPIENTS = ["女朋友", "男朋友", "朋友", "妈妈", "母亲", "老师", "同学", "爱人", "家人"]
STYLE_KEYWORDS = ["温柔", "高级", "浪漫", "清新", "热烈", "正式", "可爱", "自然", "明亮", "优雅"]
CONFIRM_WORDS = ["满意", "确认", "下单", "可以", "就这个", "没问题"]


def handle_message(session_id: str | None, message: str) -> AgentMessageResponse:
    active_session_id = session_id or str(uuid.uuid4())
    state = SESSIONS.setdefault(active_session_id, _new_state())
    state["trace"] = []
    state["llmModel"] = _get_model()

    if _is_confirm_message(message) and state.get("proposal"):
        _add_trace(state, "human_confirmation", "human", "success", "User confirmed the current proposal.")
        response = _confirm_order(active_session_id, state)
        SESSIONS[active_session_id] = state
        return response

    parsed, parser_mode = _parse_requirement(message)
    state["parserMode"] = parser_mode
    _add_trace(
        state,
        "parse_requirement",
        "llm" if parser_mode == "llm" else "control",
        "success" if parser_mode == "llm" else "fallback",
        f"Parsed requirement with {state['llmModel']}." if parser_mode == "llm" else "Used rule-based parser fallback.",
    )
    _merge_requirement(state["requirement"], parsed)

    if state.get("stage") == "waiting_confirmation":
        _apply_revision(state["requirement"], message)

    state = _run_design_graph(state)
    SESSIONS[active_session_id] = state

    if state["stage"] == "clarifying":
        return _response(
            active_session_id,
            state,
            reply=state["reply"],
            next_actions=["answer_questions"],
        )

    return _response(
        active_session_id,
        state,
        reply=state["reply"],
        next_actions=["confirm", "revise"],
    )


def _build_design_graph():
    graph = StateGraph(WorkflowState)
    graph.add_node("validate_requirements", _validate_requirements_node)
    graph.add_node("clarify_requirements", _clarify_requirements_node)
    graph.add_node("check_inventory", _check_inventory_node)
    graph.add_node("generate_proposal", _generate_proposal_node)

    graph.add_edge(START, "validate_requirements")
    graph.add_conditional_edges(
        "validate_requirements",
        _route_after_validation,
        {
            "clarify_requirements": "clarify_requirements",
            "check_inventory": "check_inventory",
        },
    )
    graph.add_edge("clarify_requirements", END)
    graph.add_edge("check_inventory", "generate_proposal")
    graph.add_edge("generate_proposal", END)
    return graph.compile()


def _run_design_graph(state: SessionState) -> SessionState:
    result = DESIGN_GRAPH.invoke({"session": state, "route": "generate"})
    return result["session"]


def _validate_requirements_node(graph_state: WorkflowState) -> WorkflowState:
    state = graph_state["session"]
    missing = _missing_fields(state["requirement"])

    if missing:
        state["stage"] = "clarifying"
        state["reply"] = _build_clarifying_reply(missing)
        _add_trace(
            state,
            "validate_requirements",
            "control",
            "waiting",
            f"Missing fields: {', '.join(missing)}.",
        )
        return {"session": state, "route": "clarify"}

    state["stage"] = "checking_inventory"
    _add_trace(state, "validate_requirements", "control", "success", "Requirement is complete enough to continue.")
    return {"session": state, "route": "generate"}


def _route_after_validation(graph_state: WorkflowState) -> Literal["clarify_requirements", "check_inventory"]:
    return "clarify_requirements" if graph_state["route"] == "clarify" else "check_inventory"


def _clarify_requirements_node(graph_state: WorkflowState) -> WorkflowState:
    _add_trace(graph_state["session"], "clarify_requirements", "control", "waiting", "Asked user for missing information.")
    return graph_state


def _check_inventory_node(graph_state: WorkflowState) -> WorkflowState:
    state = graph_state["session"]
    state["stage"] = "checking_inventory"
    _ensure_default_quantities(state["requirement"])
    state["inventoryCheck"] = check_inventory(
        state["requirement"].flowers,
        state["requirement"].style,
    )
    shortage_count = sum(1 for item in state["inventoryCheck"] if not item.enough)
    detail = (
        f"Checked {len(state['inventoryCheck'])} requested materials; {shortage_count} shortage."
        if shortage_count
        else f"Checked {len(state['inventoryCheck'])} requested materials; all available."
    )
    _add_trace(state, "check_inventory", "tool", "success", detail)
    return {"session": state, "route": "generate"}


def _generate_proposal_node(graph_state: WorkflowState) -> WorkflowState:
    state = graph_state["session"]
    state["stage"] = "generating_proposal"
    fallback_proposal = _build_proposal(state["requirement"], state["inventoryCheck"])
    _add_trace(
        state,
        "price_and_constraints",
        "tool",
        "success",
        f"Locked materials, packaging, and estimated price: {fallback_proposal.estimatedPrice}.",
    )
    state["proposal"], proposal_used_llm = build_proposal_with_llm(
        state["requirement"],
        state["inventoryCheck"],
        fallback_proposal,
    )
    _add_trace(
        state,
        "generate_proposal",
        "llm" if proposal_used_llm else "control",
        "success" if proposal_used_llm else "fallback",
        f"Polished proposal with {state['llmModel']}." if proposal_used_llm else "Used deterministic proposal fallback.",
    )
    state["imagePrompt"] = build_image_prompt(state["proposal"])
    state["imageUrl"] = mock_image_url(state["proposal"])
    _add_trace(state, "generate_preview", "tool", "success", "Generated SVG bouquet preview from locked proposal data.")
    state["stage"] = "waiting_confirmation"

    reply = (
        "我已经根据你的需求和当前库存生成了一版定制花束方案。"
        "你可以确认下单，也可以继续说想调整颜色、包装、花材或整体风格。"
    )
    if any(not item.enough for item in state["inventoryCheck"]):
        reply = (
            "有部分花材库存不足，我已经按相近风格推荐了可制作的替代方案。"
            "下面是当前可落地的一版花束设计。"
        )

    state["reply"] = reply
    return {"session": state, "route": "generate"}


def _new_state() -> SessionState:
    return {
        "stage": "collecting_requirements",
        "parserMode": "rule_based",
        "llmModel": None,
        "trace": [],
        "reply": "",
        "requirement": BouquetRequirement(),
        "inventoryCheck": [],
        "proposal": None,
        "imagePrompt": None,
        "imageUrl": None,
        "orderDraft": None,
    }


def _parse_requirement(message: str) -> tuple[BouquetRequirement, ParserMode]:
    llm_result = parse_requirement_with_llm(message)
    if llm_result:
        return llm_result, "llm"
    return _parse_requirement_rule_based(message), "rule_based"


def _parse_requirement_rule_based(message: str) -> BouquetRequirement:
    budget = _parse_budget(message)
    recipient = _first_match(message, RECIPIENTS)
    style_words = [word for word in STYLE_KEYWORDS if word in message]
    packaging = _parse_packaging(message)
    flowers = _parse_flowers(message)

    occasion = None
    if "生日" in message:
        occasion = "生日"
    elif "告白" in message or "表白" in message:
        occasion = "告白"
    elif "纪念日" in message:
        occasion = "纪念日"
    elif "毕业" in message:
        occasion = "毕业"

    return BouquetRequirement(
        recipient=recipient,
        occasion=occasion,
        budget=budget,
        style="、".join(style_words) if style_words else None,
        flowers=flowers,
        packaging=packaging,
    )


def _parse_budget(message: str) -> int | None:
    patterns = [r"预算\s*(\d+)", r"(\d+)\s*元", r"(\d+)\s*块"]
    for pattern in patterns:
        match = re.search(pattern, message)
        if match:
            return int(match.group(1))
    return None


def _parse_packaging(message: str) -> str | None:
    if "包装" not in message:
        return None
    if "高级" in message or "香槟" in message:
        return "香槟色高级包装纸"
    if "粉" in message:
        return "粉色雾面包装纸"
    if "白" in message:
        return "白色简约包装纸"
    return "商家推荐包装"


def _parse_flowers(message: str) -> list[FlowerRequest]:
    flowers: list[FlowerRequest] = []
    for flower_name in KNOWN_FLOWERS:
        if flower_name not in message:
            continue
        quantity = None
        quantity_match = re.search(rf"(\d+)\s*[枝朵束份]?\s*{flower_name}", message)
        if quantity_match:
            quantity = int(quantity_match.group(1))
        flowers.append(FlowerRequest(name=flower_name, quantity=quantity))
    return flowers


def _first_match(message: str, candidates: list[str]) -> str | None:
    for candidate in candidates:
        if candidate in message:
            return candidate
    return None


def _merge_requirement(current: BouquetRequirement, incoming: BouquetRequirement) -> None:
    for field in ["recipient", "occasion", "budget", "style", "packaging"]:
        value = getattr(incoming, field)
        if value:
            setattr(current, field, value)

    existing_names = {flower.name for flower in current.flowers}
    for flower in incoming.flowers:
        if flower.name in existing_names:
            for current_flower in current.flowers:
                if current_flower.name == flower.name and flower.quantity:
                    current_flower.quantity = flower.quantity
        else:
            current.flowers.append(flower)

    current.constraints.extend(
        constraint for constraint in incoming.constraints if constraint not in current.constraints
    )


def _missing_fields(requirement: BouquetRequirement) -> list[str]:
    missing: list[str] = []
    if not requirement.recipient and not requirement.occasion:
        missing.append("送礼对象或使用场景")
    if not requirement.budget:
        missing.append("预算")
    if not requirement.style:
        missing.append("整体风格")
    if not requirement.flowers:
        missing.append("花材偏好")
    return missing


def _build_clarifying_reply(missing: list[str]) -> str:
    if len(missing) == 1:
        return f"我还需要确认一下你的{missing[0]}，这样才能生成更贴合的花束方案。"
    return f"我还需要确认这些信息：{'、'.join(missing[:3])}。你可以用一句话补充，我会继续往下生成。"


def _ensure_default_quantities(requirement: BouquetRequirement) -> None:
    for flower in requirement.flowers:
        if flower.quantity:
            continue
        flower.quantity = 1 if flower.name in ["满天星", "尤加利叶"] else 6


def _build_proposal(
    requirement: BouquetRequirement,
    inventory_check: list[InventoryCheckItem],
) -> BouquetProposal:
    flowers: list[dict[str, Any]] = []
    notes: list[str] = []
    estimated_price = 0

    for checked in inventory_check:
        final_name = checked.name
        quantity = checked.requested
        unit_price = checked.unitPrice

        if not checked.enough and checked.substitute:
            final_name = checked.substitute
            substitute_item = find_item(final_name)
            unit_price = substitute_item.unitPrice if substitute_item else unit_price
            notes.append(f"{checked.name}库存不足，已建议替换为{final_name}。")

        estimated_price += (unit_price or 0) * quantity
        flowers.append({"name": final_name, "quantity": quantity, "unitPrice": unit_price})

    packaging_fee = 36 if requirement.packaging and "高级" in requirement.packaging else 20
    estimated_price += packaging_fee

    flower_meanings = []
    for flower in flowers:
        item = find_item(flower["name"])
        if item:
            flower_meanings.append(f"{item.name}代表{item.meaning}")

    title = _build_title(requirement)
    return BouquetProposal(
        title=title,
        flowers=flowers,
        packaging=requirement.packaging or "商家推荐包装",
        style=requirement.style or "自然、协调",
        meaning="；".join(flower_meanings) or "整体表达真诚祝福与美好心意。",
        estimatedPrice=estimated_price,
        notes=notes,
    )


def _build_title(requirement: BouquetRequirement) -> str:
    style = (requirement.style or "定制").split("、")[0]
    if requirement.recipient:
        return f"送给{requirement.recipient}的{style}花束"
    if requirement.occasion:
        return f"{requirement.occasion}{style}花束"
    return f"{style}定制花束"


def _apply_revision(requirement: BouquetRequirement, message: str) -> None:
    styles = [word for word in STYLE_KEYWORDS if word in message]
    if styles:
        requirement.style = "、".join(styles)
    packaging = _parse_packaging(message)
    if packaging:
        requirement.packaging = packaging


def _is_confirm_message(message: str) -> bool:
    return any(word in message for word in CONFIRM_WORDS)


def _confirm_order(session_id: str, state: SessionState) -> AgentMessageResponse:
    proposal: BouquetProposal = state["proposal"]
    state["stage"] = "confirmed"
    state["orderDraft"] = OrderDraft(
        flowers=deepcopy(proposal.flowers),
        packaging=proposal.packaging,
        style=proposal.style,
        estimatedPrice=proposal.estimatedPrice,
        merchantNote=(
            f"按「{proposal.title}」制作，整体风格为{proposal.style}。"
            f"包装使用{proposal.packaging}，注意保持花材层次和成品整洁度。"
        ),
        imageUrl=state.get("imageUrl"),
    )
    return _response(
        session_id,
        state,
        reply="已确认。我已经生成商家制作单，花店可以根据这份清单制作花束。",
        next_actions=["start_new_design"],
    )


def _response(
    session_id: str,
    state: SessionState,
    reply: str,
    next_actions: list[str],
) -> AgentMessageResponse:
    return AgentMessageResponse(
        sessionId=session_id,
        stage=state["stage"],
        parserMode=state["parserMode"],
        llmModel=state["llmModel"],
        trace=state["trace"],
        reply=reply,
        requirement=state["requirement"],
        inventoryCheck=state["inventoryCheck"],
        proposal=state["proposal"],
        imagePrompt=state["imagePrompt"],
        imageUrl=state["imageUrl"],
        orderDraft=state["orderDraft"],
        nextActions=next_actions,
    )


def _add_trace(
    state: SessionState,
    node: str,
    trace_type: Literal["llm", "tool", "control", "human"],
    status: Literal["success", "fallback", "waiting", "skipped"],
    detail: str,
) -> None:
    state.setdefault("trace", []).append(
        {
            "node": node,
            "type": trace_type,
            "status": status,
            "detail": detail,
        }
    )


DESIGN_GRAPH = _build_design_graph()
