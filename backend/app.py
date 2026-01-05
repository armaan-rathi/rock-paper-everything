import os
import random
import uuid
from dataclasses import asdict, dataclass
from typing import Dict, List

from flask import Flask, jsonify, request
from flask_cors import CORS

try:
    import openpyxl
except ImportError:
    openpyxl = None


DATA_PATH = os.getenv("OBJECTS_FILE", os.path.join(os.path.dirname(__file__), "data", "objects.csv"))


@dataclass
class GameState:
    level: int
    player_hp: int
    player_hp_max: int
    cpu_hp: int
    cpu_hp_max: int
    cpu_choices: List[Dict[str, str]]
    last_cpu_choice: Dict[str, str] | None
    last_result: str
    game_over: bool
    level_up: bool


app = Flask(__name__)
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
            if not row or row[0] is None or row[1] is None:
                continue
            objects.append({"name": str(row[0]).strip(), "type": str(row[1]).strip().lower()})
        return objects

    objects = []
    with open(DATA_PATH, "r", encoding="utf-8") as handle:
        lines = handle.read().splitlines()
    for line in lines[1:]:
        if not line.strip():
            continue
        name, rps_type = [part.strip() for part in line.split(",", maxsplit=1)]
        objects.append({"name": name, "type": rps_type.lower()})
    return objects


def random_cpu_choices(objects: List[Dict[str, str]]) -> List[Dict[str, str]]:
    if len(objects) < 3:
        return random.sample(objects, k=len(objects))
    return random.sample(objects, k=3)


def start_level(level: int, player_hp: int, player_hp_max: int, objects: List[Dict[str, str]]) -> GameState:
    cpu_hp_max = 2 + level
    cpu_choices = random_cpu_choices(objects)
    return GameState(
        level=level,
        player_hp=player_hp,
        player_hp_max=player_hp_max,
        cpu_hp=cpu_hp_max,
        cpu_hp_max=cpu_hp_max,
        cpu_choices=cpu_choices,
        last_cpu_choice=None,
        last_result="",
        game_over=False,
        level_up=False,
    )


def compare_moves(player_move: str, cpu_type: str) -> str:
    if player_move == cpu_type:
        return "tie"
    winning_pairs = {
        "rock": "scissors",
        "paper": "rock",
        "scissors": "paper",
    }
    if winning_pairs[player_move] == cpu_type:
        return "win"
    return "loss"


def apply_damage(state: GameState, result: str) -> None:
    if result == "tie":
        state.player_hp -= 1
        state.cpu_hp -= 1
    elif result == "win":
        state.cpu_hp -= 3
    else:
        state.player_hp -= 3


@app.post("/api/game/start")
def start_game():
    objects = load_objects()
    if not objects:
        return jsonify({"error": "No objects found"}), 500
    state = start_level(level=1, player_hp=15, player_hp_max=15, objects=objects)
    session_id = str(uuid.uuid4())
    _sessions[session_id] = state
    return jsonify({"session_id": session_id, "state": asdict(state)})


@app.post("/api/game/turn")
def take_turn():
    payload = request.get_json() or {}
    session_id = payload.get("session_id")
    player_move = payload.get("player_move")

    if session_id not in _sessions:
        return jsonify({"error": "Invalid session"}), 404
    if player_move not in {"rock", "paper", "scissors"}:
        return jsonify({"error": "Invalid move"}), 400

    state = _sessions[session_id]
    if state.game_over:
        return jsonify({"state": asdict(state)})

    cpu_choice = random.choice(state.cpu_choices)
    result = compare_moves(player_move, cpu_choice["type"])

    apply_damage(state, result)

    state.last_cpu_choice = cpu_choice
    state.last_result = result
    state.level_up = False

    if state.player_hp <= 0:
        state.player_hp = max(state.player_hp, 0)
        state.game_over = True
        return jsonify({"state": asdict(state)})

    if state.cpu_hp <= 0:
        state.level += 1
        state.level_up = True
        objects = load_objects()
        next_state = start_level(state.level, state.player_hp, state.player_hp_max, objects)
        next_state.last_cpu_choice = state.last_cpu_choice
        next_state.last_result = state.last_result
        next_state.level_up = True
        _sessions[session_id] = next_state
        return jsonify({"state": asdict(next_state)})

    return jsonify({"state": asdict(state)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
