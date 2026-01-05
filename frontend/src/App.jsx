import { useEffect, useMemo, useState } from "react";

const TYPE_ICONS = {
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
  const [showLevelUp, setShowLevelUp] = useState(false);

  const resultMessage = useMemo(() => {
    if (!gameState?.last_result) {
      if (gameState?.awaiting_player) {
        return "CPU locked in. Choose your response.";
      }
      return "CPU is weighing its options...";
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

  const selectCpuChoice = async () => {
    if (!sessionId) {
      return;
    }
    try {
      const response = await fetch("/api/game/cpu-select", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Unable to select CPU move");
      }
      setGameState(data.state);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleMove = async (item) => {
    if (!sessionId) {
      return;
    }
    setAnimatingMove(item);
    try {
      const response = await fetch("/api/game/turn", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, player_item_id: item.id }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Unable to resolve turn");
      }
      setGameState(data.state);
    } catch (err) {
      setError(err.message);
    } finally {
      setTimeout(() => setAnimatingMove(null), 600);
    }
  };

  useEffect(() => {
    startGame();
  }, []);

  useEffect(() => {
    if (!gameState || gameState.game_over) {
      return;
    }
    if (!gameState.awaiting_player) {
      const timer = setTimeout(() => {
        selectCpuChoice();
      }, gameState.level_up ? 1200 : 700);
      return () => clearTimeout(timer);
    }
    return undefined;
  }, [gameState?.awaiting_player, gameState?.level_up, gameState?.game_over]);

  useEffect(() => {
    if (!gameState?.level_up) {
      return;
    }
    setShowLevelUp(true);
    const timer = setTimeout(() => setShowLevelUp(false), 1300);
    return () => clearTimeout(timer);
  }, [gameState?.level_up]);

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

  const leftItem = animatingMove || gameState.last_player_item;

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
          <p className="cpu-hint">Types are hidden. Read the names and guess the type.</p>
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
              </div>
            ))}
          </div>
          {gameState.last_cpu_choice && (
            <div className="cpu-play">
              CPU locked in <strong>{gameState.last_cpu_choice.name}</strong>
            </div>
          )}
        </div>

        <div className={`result-card ${gameState.last_result}`}>
          {showLevelUp && <div className="level-banner">LEVEL UP</div>}
          <p className="result-label">{resultMessage}</p>
          {gameState.last_result && (
            <div className="result-icons">
              <span className={`icon ${animatingMove ? "pulse" : ""}`}>
                {leftItem ? TYPE_ICONS[leftItem.primary_type] : "❔"}
              </span>
              <span className="vs">vs</span>
              <span className="icon">
                {gameState.last_cpu_choice
                  ? TYPE_ICONS[gameState.last_cpu_choice.primary_type]
                  : "❔"}
              </span>
            </div>
          )}
          {gameState.game_won && (
            <div className="game-over">Victory! You cleared level 10.</div>
          )}
          {gameState.game_over && !gameState.game_won && (
            <div className="game-over">Game Over. The roguelike run ends here.</div>
          )}
        </div>
      </section>

      <section className="actions">
        <div className="inventory">
          <h3>Your Items</h3>
          <div className="inventory-grid">
            {gameState.player_items.map((item) => (
              <button
                key={item.id}
                className={`inventory-item ${animatingMove?.id === item.id ? "active" : ""}`}
                onClick={() => handleMove(item)}
                disabled={!gameState.awaiting_player || gameState.game_over}
              >
                <div className="item-name">{item.name}</div>
                <div className="item-types">
                  <span>{TYPE_ICONS[item.primary_type]}</span>
                  <span>{TYPE_ICONS[item.secondary_type]}</span>
                </div>
                {!item.is_base && <div className="item-usage">Single use</div>}
              </button>
            ))}
          </div>
        </div>
        <button className="secondary" onClick={startGame}>
          Start New Run
        </button>
      </section>
    </div>
  );
}
