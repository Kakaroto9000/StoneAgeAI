"""
Convert engine objects into JSON-friendly dicts and readable text.

The engine identifies everything by integers (resource types 2-6, action
types 1-6, location indices 0-15). This module is the single place that
turns those into names the browser can show.
"""

from typing import Any, Dict, List, Optional

from stoneage_ai.game.area import Gathering
from stoneage_ai.game.building import CertainBuilding, FlexBuilding
from stoneage_ai.game.card import Card
from stoneage_ai.game.game import Game
from stoneage_ai.game.player import Player
from stoneage_ai.game.utility import Utility

RESOURCE_NAMES = {2: "food", 3: "wood", 4: "stone", 5: "clay", 6: "gold"}

PHASES = {
    1: "placement",
    2: "tools",
    3: "buy",
    4: "pay",
    5: "dice",
    6: "choose2",
}

UTILITY_LABELS = {"Farm": "Field", "House": "Hut", "ToolShop": "Tool Maker"}

# Reward for each die face on "dice roll" cards (see Game.get_reward).
DICE_REWARDS = {1: "wood", 2: "stone", 3: "clay", 4: "gold", 5: "tool", 6: "field"}

CARD_EFFECT_TEXT = {
    "add_resource": "Gain {amount} {resource}",
    "dice_roll": "Everyone picks a die reward",
    "resources_with_dice": "Roll 2 dice for {resource}",
    "add_vp": "Gain {vp} VP",
    "add_tool": "Gain a tool",
    "add_wheat": "Gain a field",
    "draw_card": "Draw a bonus card",
    "one_use_tool": "One-use tool +{tool}",
    "any_2_resources": "Take any 2 resources",
}

MULTIPLIER_NAMES = {1: "tools", 2: "buildings", 3: "people", 4: "fields"}


def location_label(location: Any, index: int) -> str:
    if isinstance(location, Utility):
        return UTILITY_LABELS.get(location.name(), location.name())
    if isinstance(location, Gathering):
        name = RESOURCE_NAMES[location.resource_type]
        return "Hunting" if name == "food" else name.capitalize()
    if isinstance(location, Card):
        return f"Card {index - 7}"
    if isinstance(location, (CertainBuilding, FlexBuilding)):
        return f"Building {index - 11}"
    return f"Slot {index}"


def card_scoring(card: Card) -> Dict[str, Any]:
    """Describe the end-game part of a card (culture symbol or multiplier)."""
    value = card.end_game_effect()
    if value is None:
        return {"kind": "none", "text": ""}
    if value < 10:
        return {"kind": "culture", "symbol": value, "text": f"Culture #{value}"}
    target, amount = value // 10, value % 10
    return {
        "kind": "multiplier",
        "text": f"{amount} VP x {MULTIPLIER_NAMES.get(target, '?')}",
    }


def card_effect_text(card: Card) -> str:
    data = card.data
    template = CARD_EFFECT_TEXT.get(card.card_type, card.card_type)
    return template.format(
        amount=data.get("amount", 1),
        resource=RESOURCE_NAMES.get(data.get("resources", data.get("resource_type", 2)), "?"),
        vp=data.get("add_vp", 3),
        tool=data.get("tool_value", 1),
    )


def building_cost(building: Any) -> Dict[str, Any]:
    if isinstance(building, CertainBuilding):
        names = [RESOURCE_NAMES[r] for r in building.resources]
        return {"kind": "fixed", "resources": names, "text": " + ".join(names),
                "vp": sum(building.resources)}
    if building.resources_require_count == 7:
        return {"kind": "flex", "text": "1-7 resources of any kind", "vp": None}
    return {
        "kind": "flex",
        "text": f"{building.resources_require_count} resources of {building.variety} kinds",
        "vp": None,
    }


def serialize_location(game: Game, location: Any, index: int) -> Optional[Dict[str, Any]]:
    if location is None:
        return None
    data: Dict[str, Any] = {
        "index": index,
        "label": location_label(location, index),
        "capacity": location.capacity,
        "occupants": [location.occupants.get(p, 0) for p in range(len(game.players))],
    }
    if isinstance(location, Utility):
        data["kind"] = "utility"
    elif isinstance(location, Gathering):
        data["kind"] = "gathering"
        data["resource"] = RESOURCE_NAMES[location.resource_type]
        data["supply"] = location.get_total_resources()
        data["divisor"] = location.resource_type
    elif isinstance(location, Card):
        data["kind"] = "card"
        data["cost"] = location.cost
        data["effect"] = card_effect_text(location)
        data["scoring"] = card_scoring(location)
    else:
        data["kind"] = "building"
        data["price"] = building_cost(location)
        stack = game.buildings_in_deck.get(index - 12, [])
        data["stack"] = len(stack)
    return data


def serialize_player(player: Player, index: int, is_human: bool) -> Dict[str, Any]:
    return {
        "index": index,
        "is_human": is_human,
        "vp": player.get_vp(),
        "resources": {RESOURCE_NAMES[k]: v for k, v in player.resources.items()},
        "fields": player.wheat,
        "workers": player.total_workers,
        "available_workers": player.available_workers,
        "tools": [{"value": t[0], "ready": bool(t[1])} for t in player.tools],
        "one_use_tools": list(player.one_use_tools),
        "buildings": player.building_num,
        "culture": [list(player.card_effects[0]), list(player.card_effects[1])],
        "multipliers": {MULTIPLIER_NAMES[k]: v for k, v in player.multipliers.items()},
    }


def legal_actions(game: Game) -> List[Dict[str, Any]]:
    """List every legal action as {index, args}, args shaped by phase."""
    system = game.action_system
    mask = game.get_mask()
    phase = game.current_type_of_action
    result = []
    for index in mask.nonzero()[0]:
        action = system.get_action(int(index))
        if phase == 1:
            args = {"location": action[0], "workers": action[1]}
        elif phase == 2:
            args = {"tools": list(action)}
        elif phase == 3:
            args = {"buy": bool(action[0])}
        elif phase == 4:
            spent = [r for r in action if r]
            args = {"pay": {RESOURCE_NAMES[r]: spent.count(r) for r in (3, 4, 5, 6)}}
        elif phase == 5:
            args = {"die": action[0], "reward": DICE_REWARDS.get(action[0])}
        else:
            args = {"resources": [RESOURCE_NAMES[action[0]], RESOURCE_NAMES[action[1]]]}
        result.append({"index": int(index), "args": args})
    return result


def pending_decision(game: Game) -> Dict[str, Any]:
    """Extra context the UI needs to explain the current decision."""
    phase = game.current_type_of_action
    data = game.current_action_data
    info: Dict[str, Any] = {"phase": PHASES.get(phase, str(phase))}
    if phase == 2:
        info["resource"] = RESOURCE_NAMES.get(data[0])
        info["dice_total"] = data[1]
        info["divisor"] = data[0]
    elif phase in (3, 4):
        location = game.locations[data[0]]
        info["location"] = serialize_location(game, location, data[0])
    elif phase == 5:
        info["dice"] = list(data)
        info["rewards"] = DICE_REWARDS
    return info


def resource_diff(before: Dict[int, int], after: Dict[int, int]) -> str:
    parts = []
    for key in RESOURCE_NAMES:
        delta = after.get(key, 0) - before.get(key, 0)
        if delta:
            parts.append(f"{delta:+d} {RESOURCE_NAMES[key]}")
    return ", ".join(parts)


def describe_action(game: Game, action_index: int) -> str:
    """Human-readable description of an action, evaluated BEFORE it is applied."""
    action = game.action_system.get_action(action_index)
    phase = game.current_type_of_action
    if phase == 1:
        where = location_label(game.locations[action[0]], action[0])
        return f"placed {action[1]} worker{'s' if action[1] != 1 else ''} on {where}"
    if phase == 2:
        resource_type, dice = game.current_action_data[0], game.current_action_data[1]
        player = game.current_player
        bonus = sum(player.tools[i][0] for i in range(4) if action[i])
        bonus += sum(v for i, v in enumerate(player.one_use_tools) if action[4 + i])
        supply = game.locations[resource_type + 1].get_total_resources()
        gained = min((dice + bonus) // resource_type, supply)
        tools = f" + {bonus} from tools" if bonus else ""
        return f"rolled {dice}{tools} for {RESOURCE_NAMES[resource_type]} (+{gained})"
    if phase == 3:
        where = location_label(game.locations[game.current_action_data[0]],
                               game.current_action_data[0])
        return f"{'bought' if action[0] else 'passed on'} {where}"
    if phase == 4:
        spent = [RESOURCE_NAMES[r] for r in action if r]
        return f"paid {', '.join(spent)}"
    if phase == 5:
        return f"took die {action[0]} ({DICE_REWARDS.get(action[0])})"
    if phase == 6:
        return f"took {RESOURCE_NAMES[action[0]]} and {RESOURCE_NAMES[action[1]]}"
    return f"action {action_index}"
