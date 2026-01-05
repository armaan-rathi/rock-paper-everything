import os
import random
import uuid
from dataclasses import asdict, dataclass
from typing import Dict, List

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

try:
    import openpyxl
except ImportError:
    openpyxl = None


ROOT_DIR = os.path.dirname(__file__)
DATA_PATH = os.getenv("OBJECTS_FILE", os.path.join(ROOT_DIR, "data", "objects.csv"))
DIST_DIR = os.path.abspath(os.path.join(ROOT_DIR, "..", "frontend", "dist"))
BASE_ITEMS = [
    {
        "id": "base-rock",
        "name": "Rock",
        "primary_type": "rock",
        "secondary_type": "rock",
        "uses_left": 3,
    },
    {
        "id": "base-paper",
        "name": "Paper",
        "primary_type": "paper",
        "secondary_type": "paper",
        "uses_left": 3,
    },
    {
        "id": "base-scissors",
        "name": "Scissors",
        "primary_type": "scissors",
        "secondary_type": "scissors",
        "uses_left": 3,
    },
    {
        "id": "base-lizard",
        "name": "Lizard",
        "primary_type": "lizard",
        "secondary_type": "lizard",
        "uses_left": 3,
    },
    {
        "id": "base-spock",
        "name": "Spock",
        "primary_type": "spock",
        "secondary_type": "spock",
        "uses_left": 3,
    },
]


@dataclass
class GameState:
    level: int
    player_hp: int
    player_hp_max: int
    cpu_hp: int
    cpu_hp_max: int
    cpu_choices: List[Dict[str, str]]
    player_items: List[Dict[str, str]]
    last_cpu_choice: Dict[str, str] | None
    last_player_item: Dict[str, str] | None
    last_result: str
    game_over: bool
    game_won: bool
    level_up: bool
    awaiting_player: bool


app = Flask(__name__, static_folder=DIST_DIR, static_url_path="")
CORS(app)

_sessions: Dict[str, GameState] = {}


def load_objects() -> List[Dict[str, str]]:
    if DATA_PATH.lower().endswith(".xlsx"):
        if openpyxl is None:
            raise RuntimeError("openpyxl is required to read .xlsx files")
        workbook = openpyxl.load_workbook(DATA_PATH)
        sheet = workbook.active
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            return []
        objects = []
        for row in rows[1:]:
            if not row or row[0] is None or row[1] is None or row[2] is None:
                continue
            objects.append(
                {
                    "name": str(row[0]).strip(),
                    "primary_type": str(row[1]).strip().lower(),
                    "secondary_type": str(row[2]).strip().lower(),
                    "uses_left": 1,
                }
            )
        return objects

    objects = []
    with open(DATA_PATH, "r", encoding="utf-8") as handle:
        lines = handle.read().splitlines()
    for line in lines[1:]:
        if not line.strip():
            continue
        name, primary_type, secondary_type = [part.strip() for part in line.split(",", maxsplit=2)]
        objects.append(
            {
                "name": name,
                "primary_type": primary_type.lower(),
                "secondary_type": secondary_type.lower(),
                "uses_left": 1,
            }
        )
    return objects


def random_cpu_choices(objects: List[Dict[str, str]]) -> List[Dict[str, str]]:
    if len(objects) < 3:
        return random.sample(objects, k=len(objects))
    return random.sample(objects, k=3)


def start_level(
    level: int,
    player_hp: int,
    player_hp_max: int,
    objects: List[Dict[str, str]],
    player_items: List[Dict[str, str]],
) -> GameState:
    cpu_hp_max = 4 + level
    cpu_choices = random_cpu_choices(objects)
    return GameState(
        level=level,
        player_hp=player_hp,
        player_hp_max=player_hp_max,
        cpu_hp=cpu_hp_max,
        cpu_hp_max=cpu_hp_max,
        cpu_choices=cpu_choices,
        player_items=player_items,
        last_cpu_choice=None,
        last_player_item=None,
        last_result="",
        game_over=False,
        game_won=False,
        level_up=False,
        awaiting_player=False,
    )


def compare_types(attacker: str, defender: str) -> str:
    if attacker == defender:
        return "tie"
    winning_pairs = {
        "rock": {"scissors", "lizard"},
        "paper": {"rock", "spock"},
        "scissors": {"paper", "lizard"},
        "lizard": {"paper", "spock"},
        "spock": {"rock", "scissors"},
    }
    if defender in winning_pairs[attacker]:
        return "win"
    return "loss"


def resolve_clash(player_item: Dict[str, str], cpu_item: Dict[str, str]) -> str:
    primary_result = compare_types(player_item["primary_type"], cpu_item["primary_type"])
    if primary_result != "tie":
        return primary_result
    return compare_types(player_item["secondary_type"], cpu_item["secondary_type"])


def apply_damage(state: GameState, result: str) -> None:
    if result == "tie":
        state.player_hp -= 1
        state.cpu_hp -= 1
    elif result == "win":
        state.cpu_hp -= 3
    else:
        state.player_hp -= 3


def build_player_items() -> List[Dict[str, str]]:
    return [item.copy() for item in BASE_ITEMS]


def award_loot(state: GameState) -> None:
    for item in state.cpu_choices:
        state.player_items.append(
            {
                "id": str(uuid.uuid4()),
                "name": item["name"],
                "primary_type": item["primary_type"],
                "secondary_type": item["secondary_type"],
                "uses_left": 1,
            }
        )


def consume_item(state: GameState, item_id: str) -> None:
    for item in state.player_items:
        if item["id"] == item_id and item["uses_left"] > 0:
            item["uses_left"] -= 1
            break


@app.post("/api/game/start")
def start_game():
    objects = load_objects()
    if not objects:
        return jsonify({"error": "No objects found"}), 500
    state = start_level(
        level=1,
        player_hp=15,
        player_hp_max=15,
        objects=objects,
        player_items=build_player_items(),
    )
    session_id = str(uuid.uuid4())
    _sessions[session_id] = state
    return jsonify({"session_id": session_id, "state": asdict(state)})


@app.post("/api/game/cpu-select")
def cpu_select():
    payload = request.get_json() or {}
    session_id = payload.get("session_id")

    if session_id not in _sessions:
        return jsonify({"error": "Invalid session"}), 404

    state = _sessions[session_id]
    if state.game_over:
        return jsonify({"state": asdict(state)})

    if state.awaiting_player and state.last_cpu_choice:
        return jsonify({"state": asdict(state)})

    state.last_cpu_choice = random.choice(state.cpu_choices)
    state.awaiting_player = True
    state.last_result = ""
    state.last_player_item = None
    return jsonify({"state": asdict(state)})


@app.post("/api/game/turn")
def take_turn():
    payload = request.get_json() or {}
    session_id = payload.get("session_id")
    player_item_id = payload.get("player_item_id")

    if session_id not in _sessions:
        return jsonify({"error": "Invalid session"}), 404

    state = _sessions[session_id]
    if state.game_over:
        return jsonify({"state": asdict(state)})
    if not state.awaiting_player or not state.last_cpu_choice:
        return jsonify({"error": "CPU has not selected a move"}), 400

    player_item = next((item for item in state.player_items if item["id"] == player_item_id), None)
    if player_item is None:
        return jsonify({"error": "Invalid player item"}), 400
    if player_item["uses_left"] <= 0:
        return jsonify({"error": "Item has no uses left"}), 400

    result = resolve_clash(player_item, state.last_cpu_choice)

    apply_damage(state, result)

    state.last_player_item = player_item
    state.last_result = result
    state.level_up = False
    state.awaiting_player = False

    consume_item(state, player_item_id)

    if state.player_hp <= 0:
        state.player_hp = max(state.player_hp, 0)
        state.game_over = True
        return jsonify({"state": asdict(state)})

    if state.cpu_hp <= 0:
        award_loot(state)
        if state.level >= 10:
            state.game_over = True
            state.game_won = True
            return jsonify({"state": asdict(state)})

        state.level += 1
        state.level_up = True
        objects = load_objects()
        next_state = start_level(
            state.level,
            state.player_hp,
            state.player_hp_max,
            objects,
            state.player_items,
        )
        next_state.last_cpu_choice = state.last_cpu_choice
        next_state.last_player_item = state.last_player_item
        next_state.last_result = state.last_result
        next_state.level_up = True
        _sessions[session_id] = next_state
        return jsonify({"state": asdict(next_state)})

    return jsonify({"state": asdict(state)})


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path: str):
    if path.startswith("api"):
        return jsonify({"error": "Not found"}), 404
    if path and os.path.exists(os.path.join(DIST_DIR, path)):
        return send_from_directory(DIST_DIR, path)
    return send_from_directory(DIST_DIR, "index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
