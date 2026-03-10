import { useState } from "react";

const AGENT_COLORS = {
  evidence: "#00d2a0",
  skeptic: "#ff6b6b",
  connector: "#4da6ff",
  methodology: "#ffa94d",
};

const AGENT_ICONS = {
  evidence: "🔬",
  skeptic: "⚔️",
  connector: "🔗",
  methodology: "📋",
};

export default function CouncilView({ agentResponses }) {
  const [expanded, setExpanded] = useState(null);

  if (!agentResponses || agentResponses.length === 0) {
    return <p style={{ color: "var(--text-muted)", fontSize: 13 }}>No agent responses.</p>;
  }

  return (
    <div className="agent-cards">
      {agentResponses.map((agent, i) => {
        const isOpen = expanded === i;
        const color = AGENT_COLORS[agent.role] || "var(--accent)";
        const icon = AGENT_ICONS[agent.role] || "🤖";

        return (
          <div
            key={i}
            className={`agent-card ${isOpen ? "expanded" : ""}`}
            onClick={() => setExpanded(isOpen ? null : i)}
          >
            <div className="agent-header">
              <span style={{ fontSize: 16 }}>{icon}</span>
              <span className="agent-dot" style={{ background: color }} />
              <span className="agent-name">{agent.agent_name}</span>
              <span className="agent-model">{agent.model}</span>
            </div>
            {isOpen && (
              <div className="agent-text">{agent.response}</div>
            )}
            {!isOpen && (
              <div className="agent-text" style={{ maxHeight: 48, overflow: "hidden", opacity: 0.6 }}>
                {agent.response.slice(0, 150)}…
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
