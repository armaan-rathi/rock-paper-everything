import { useEffect, useMemo, useState } from "react";

const MOVE_ICONS = {
  rock: "🪨",
  paper: "📜",
  scissors: "✂️",
};

const RESULT_COPY = {
  win: "You win the clash!",
  loss: "You took a hit!",
  tie: "Stalemate!",
};

function HealthBar({ current, max, label }) {
  const percent = Math.max(0, Math.min(100, (current / max) * 100));
  return (
    <div className="health-card">
      <div className="health-header">
        <span>{label}</span>
        <span>
          {current}/{max}
        </span>
      </div>
      <div className="health-bar">
        <div className="health-fill" style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}

export default function App() {
  const [sessionId, setSessionId] = useState(null);
  const [gameState, setGameState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [animatingMove, setAnimatingMove] = useState(null);

  const resultMessage = useMemo(() => {
    if (!gameState?.last_result) {
      return "Make your move to begin.";
    }
    return RESULT_COPY[gameState.last_result];
  }, [gameState]);

  const startGame = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/game/start", { method: "POST" });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Unable to start game");
      }
      setSessionId(data.session_id);
      setGameState(data.state);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleMove = async (move) => {
    if (!sessionId) {
      return;
    }
    setAnimatingMove(move);
    try {
      const response = await fetch("/api/game/turn", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, player_move: move }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Unable to resolve turn");
      }
      setGameState(data.state);
    } catch (err) {
      setError(err.message);
    } finally {
      setTimeout(() => setAnimatingMove(null), 500);
    }
  };

  useEffect(() => {
    startGame();
  }, []);

  if (loading) {
    return <div className="screen">Loading the arena...</div>;
  }

  if (error) {
    return (
      <div className="screen">
        <h2>Something went wrong</h2>
        <p>{error}</p>
        <button className="primary" onClick={startGame}>
          Retry
        </button>
      </div>
    );
  }

  if (!gameState) {
    return null;
  }

  return (
    <div className="app">
      <header className="header">
        <div>
          <p className="eyebrow">Roguelike Clash</p>
          <h1>Rock Paper Everything</h1>
        </div>
        <div className="level">Level {gameState.level}</div>
      </header>

      <section className="status-grid">
        <HealthBar
          current={gameState.player_hp}
          max={gameState.player_hp_max}
          label="Player"
        />
        <HealthBar
          current={gameState.cpu_hp}
          max={gameState.cpu_hp_max}
          label="CPU"
        />
      </section>

      <section className="arena">
        <div className="cpu-panel">
          <h2>CPU Loadout</h2>
          <div className="cpu-choices">
            {gameState.cpu_choices.map((choice) => (
              <div
                key={choice.name}
                className={
                  gameState.last_cpu_choice?.name === choice.name
                    ? "cpu-choice active"
                    : "cpu-choice"
                }
              >
                <span>{choice.name}</span>
                <span className="tag">{choice.type}</span>
              </div>
            ))}
          </div>
          {gameState.last_cpu_choice && (
            <div className="cpu-play">
              CPU played <strong>{gameState.last_cpu_choice.name}</strong>
            </div>
          )}
        </div>

        <div className={`result-card ${gameState.last_result}`}>
          <p className="result-label">{resultMessage}</p>
          {gameState.last_result && (
            <div className="result-icons">
              <span className={`icon ${animatingMove ? "pulse" : ""}`}>
                {MOVE_ICONS[animatingMove || "rock"]}
              </span>
              <span className="vs">vs</span>
              <span className="icon">
                {gameState.last_cpu_choice
                  ? MOVE_ICONS[gameState.last_cpu_choice.type]
                  : "❔"}
              </span>
            </div>
          )}
          {gameState.level_up && (
            <div className="level-up">Level up! New challenger approaches.</div>
          )}
          {gameState.game_over && (
            <div className="game-over">Game Over. The roguelike run ends here.</div>
          )}
        </div>
      </section>

      <section className="actions">
        {Object.keys(MOVE_ICONS).map((move) => (
          <button
            key={move}
            className={`move ${animatingMove === move ? "active" : ""}`}
            onClick={() => handleMove(move)}
            disabled={gameState.game_over}
          >
            <span className="move-icon">{MOVE_ICONS[move]}</span>
            <span className="move-label">{move}</span>
          </button>
        ))}
        <button className="secondary" onClick={startGame}>
          Start New Run
        </button>
      </section>
    </div>
  );
}
