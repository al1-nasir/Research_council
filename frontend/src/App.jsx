import { useState, useEffect, useRef } from "react";
import { Plus, FlaskConical, Activity, Search, BookOpen, Network, FolderPlus } from "lucide-react";
import QueryInput from "./components/QueryInput";
import CouncilView from "./components/CouncilView";
import EvidenceTrail from "./components/EvidenceTrail";
import GraphViewer from "./components/GraphViewer";
import PubMedSearch from "./components/PubMedSearch";
import UnifiedSearch from "./components/UnifiedSearch";
import IngestedPapers from "./components/IngestedPapers";
import { sendQuery, fetchGraph, healthCheck, getGraphStorages, deleteGraphStorage } from "./api";

/* ── Helpers ────────────────────────────────────────────── */

function confColor(c) {
  if (c >= 0.7) return "var(--green)";
  if (c >= 0.4) return "var(--orange)";
  return "var(--red)";
}

const EXAMPLES = [
  { label: "Contradiction", text: "Are there contradictions in BRCA1's role in triple-negative breast cancer?" },
  { label: "Hypothesis", text: "Has anyone tested repurposing metformin for glioblastoma?" },
  { label: "Review", text: "Summarize recent evidence on GLP-1 agonists and neurodegeneration" },
];

/* ── App ────────────────────────────────────────────────── */

export default function App() {
  const [sessions, setSessions] = useState([{ id: 1, title: "New research", messages: [] }]);
  const [activeId, setActiveId] = useState(1);
  const [loading, setLoading] = useState(false);
  const [online, setOnline] = useState(false);
  const [showPubMedSearch, setShowPubMedSearch] = useState(false);
  const [showIngestedPapers, setShowIngestedPapers] = useState(false);
  const [showFullscreenGraph, setShowFullscreenGraph] = useState(false);
  const [graphData, setGraphData] = useState(null);
  const [graphStorages, setGraphStorages] = useState(["default"]);
  const [selectedGraphStorage, setSelectedGraphStorage] = useState("default");
  const chatRef = useRef(null);

  const session = sessions.find((s) => s.id === activeId);
  const messages = session?.messages || [];

  /* Load graph storages on mount */
  useEffect(() => {
    loadGraphStorages();
  }, []);

  const loadGraphStorages = async () => {
    try {
      const storages = await getGraphStorages();
      setGraphStorages(storages && storages.length > 0 ? storages : ["default"]);
    } catch (err) {
      console.error("Failed to load graph storages:", err);
      setGraphStorages(["default"]);
    }
  };

  /* Health check on mount */
  useEffect(() => {
    healthCheck().then(setOnline);
    const iv = setInterval(() => healthCheck().then(setOnline), 30_000);
    return () => clearInterval(iv);
  }, []);

  /* Auto-scroll */
  useEffect(() => {
    if (chatRef.current) chatRef.current.scrollTop = chatRef.current.scrollHeight;
  }, [messages, loading]);

  /* ── Send query ───────────────────────────────────────── */
  const handleSend = async (query) => {
    const userMsg = { role: "user", text: query };
    updateMessages([...messages, userMsg]);

    /* Update session title from first message */
    if (messages.length === 0) {
      setSessions((prev) =>
        prev.map((s) => (s.id === activeId ? { ...s, title: query.slice(0, 50) } : s))
      );
    }

    setLoading(true);
    try {
      const [result, graphData] = await Promise.all([
        sendQuery(query, selectedGraphStorage),
        fetchGraph(null, "Paper", 50, selectedGraphStorage).catch(() => null),
      ]);

      const botMsg = {
        role: "bot",
        text: result.summary || "No summary returned.",
        data: result,
        graph: graphData,
      };
      updateMessages([...messages, userMsg, botMsg]);
    } catch (err) {
      const errMsg = { role: "bot", text: `❌ Error: ${err.message}`, data: null };
      updateMessages([...messages, userMsg, errMsg]);
    } finally {
      setLoading(false);
    }
  };

  const updateMessages = (msgs) => {
    setSessions((prev) =>
      prev.map((s) => (s.id === activeId ? { ...s, messages: msgs } : s))
    );
  };

  /* ── New chat ─────────────────────────────────────────── */
  const newChat = () => {
    const id = Date.now();
    setSessions((prev) => [...prev, { id, title: "New research", messages: [] }]);
    setActiveId(id);
  };

  return (
    <div className="app">
      {/* ── Sidebar ──────────────────────────────────────── */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="icon">🧬</div>
          <div>
            <h1>Research Council</h1>
            <span>GraphRAG + Multi-LLM</span>
          </div>
        </div>

        <button className="new-chat-btn" onClick={newChat}>
          <Plus size={14} /> New Research
        </button>

        <button className="new-chat-btn pubmed-btn" onClick={() => setShowPubMedSearch(true)}>
          <Search size={14} /> Search Papers
        </button>

        <button className="new-chat-btn papers-btn" onClick={() => setShowIngestedPapers(true)}>
          <BookOpen size={14} /> Ingested Papers
        </button>

        <button className="new-chat-btn graph-btn" onClick={async () => {
          try {
            const data = await fetchGraph(null, "Paper", 50, selectedGraphStorage);
            setGraphData(data);
            setShowFullscreenGraph(true);
          } catch (err) {
            console.error("Failed to fetch graph:", err);
          }
        }}>
          <Network size={14} /> View Graph
        </button>

        {/* Graph Storage Selector */}
        <div className="graph-storage-selector">
          <div className="storage-label">
            <FolderPlus size={14} /> Graph:
          </div>
          <select 
            value={selectedGraphStorage} 
            onChange={(e) => setSelectedGraphStorage(e.target.value)}
            className="storage-select"
          >
            {graphStorages.map((storage) => (
              <option key={storage} value={storage}>{storage}</option>
            ))}
          </select>
        </div>

        <div className="session-list">
          {sessions.map((s) => (
            <div
              key={s.id}
              className={`session-item ${s.id === activeId ? "active" : ""}`}
              onClick={() => setActiveId(s.id)}
            >
              {s.title}
            </div>
          ))}
        </div>
      </aside>

      {/* ── Main ─────────────────────────────────────────── */}
      <div className="main">
        <div className="chat-area" ref={chatRef}>
          {messages.length === 0 && !loading ? (
            <Welcome onExample={handleSend} />
          ) : (
            <div className="messages">
              {messages.map((m, i) => (
                <Message key={i} msg={m} />
              ))}
              {loading && <ThinkingBubble />}
            </div>
          )}
        </div>

        <QueryInput onSend={handleSend} disabled={loading} />

        <div className="status-bar">
          <span className={`status-dot ${online ? "" : "offline"}`} />
          <span>{online ? "Backend connected" : "Backend offline"}</span>
          <span style={{ marginLeft: "auto" }}>
            {messages.filter((m) => m.data).length} queries this session
          </span>
        </div>
      </div>

      {showPubMedSearch && (
        <UnifiedSearch 
          onClose={() => setShowPubMedSearch(false)} 
          onIngest={() => {
            // Optionally trigger a graph refresh after ingestion
          }}
        />
      )}

      {showIngestedPapers && (
        <IngestedPapers 
          onClose={() => setShowIngestedPapers(false)} 
        />
      )}

      {showFullscreenGraph && graphData && (
        <div className="fullscreen-graph-overlay" onClick={() => setShowFullscreenGraph(false)}>
          <div className="fullscreen-graph-modal" onClick={(e) => e.stopPropagation()}>
            <GraphViewer 
              graphData={graphData} 
              fullscreen={true}
              onClose={() => setShowFullscreenGraph(false)}
            />
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Welcome screen ────────────────────────────────────── */

function Welcome({ onExample }) {
  return (
    <div className="welcome">
      <div className="logo-big">🧬</div>
      <h2>Research Council</h2>
      <p>
        Ask any biomedical research question. The council of 4 AI agents will
        deliberate over the knowledge graph, cross-review each other, and deliver
        a confidence-scored, cited answer.
      </p>
      <div className="welcome-cards">
        {EXAMPLES.map((ex, i) => (
          <div key={i} className="welcome-card" onClick={() => onExample(ex.text)}>
            <div className="label">{ex.label}</div>
            <div className="text">{ex.text}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Message component ─────────────────────────────────── */

function Message({ msg }) {
  const [tab, setTab] = useState("answer");

  if (msg.role === "user") {
    return (
      <div className="message user">
        <div className="msg-avatar user">👤</div>
        <div className="msg-body">
          <div className="msg-content">{msg.text}</div>
        </div>
      </div>
    );
  }

  const d = msg.data;
  const hasData = !!d;

  return (
    <div className="message bot">
      <div className="msg-avatar bot">🧬</div>
      <div className="msg-body">
        <div className="msg-content">{msg.text}</div>

        {/* Confidence bar */}
        {hasData && d.confidence != null && (
          <div className="confidence-bar">
            <span style={{ fontWeight: 600 }}>Confidence</span>
            <div className="conf-track">
              <div
                className="conf-fill"
                style={{
                  width: `${(d.confidence * 100).toFixed(0)}%`,
                  background: confColor(d.confidence),
                }}
              />
            </div>
            <span style={{ fontFamily: "var(--mono)", fontWeight: 600, color: confColor(d.confidence) }}>
              {(d.confidence * 100).toFixed(0)}%
            </span>
          </div>
        )}

        {/* Tabs */}
        {hasData && (
          <>
            <div className="result-tabs">
              <button className={`tab-btn ${tab === "answer" ? "active" : ""}`} onClick={() => setTab("answer")}>
                Answer
              </button>
              <button className={`tab-btn ${tab === "council" ? "active" : ""}`} onClick={() => setTab("council")}>
                🧠 Council ({d.agent_responses?.length || 0})
              </button>
              <button className={`tab-btn ${tab === "evidence" ? "active" : ""}`} onClick={() => setTab("evidence")}>
                📄 Evidence
              </button>
              <button className={`tab-btn ${tab === "graph" ? "active" : ""}`} onClick={() => setTab("graph")}>
                🕸️ Graph
              </button>
            </div>

            <div className="tab-panel">
              {tab === "answer" && <AnswerPanel data={d} />}
              {tab === "council" && <CouncilView agentResponses={d.agent_responses} />}
              {tab === "evidence" && (
                <EvidenceTrail
                  citations={d.citations}
                  keyFindings={d.key_findings}
                  contradictions={d.contradictions}
                />
              )}
              {tab === "graph" && <GraphViewer graphData={msg.graph} />}
            </div>
          </>
        )}

        {/* Token count */}
        {hasData && d.total_tokens > 0 && (
          <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 10 }}>
            {d.total_tokens.toLocaleString()} tokens used •{" "}
            Agent agreement: {((d.agent_agreement || 0) * 100).toFixed(0)}%
            {d.conclusion_id && <> • Saved as <code style={{ fontFamily: "var(--mono)" }}>{d.conclusion_id}</code></>}
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Answer sub-panel ──────────────────────────────────── */

function AnswerPanel({ data }) {
  return (
    <div>
      {data.methodology_notes && (
        <div style={{ marginBottom: 12 }}>
          <h4 style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 600 }}>
            Methodology Notes
          </h4>
          <div style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.7, padding: "10px 12px", background: "var(--bg-tertiary)", borderRadius: "var(--radius-sm)", border: "1px solid var(--border)" }}>
            {data.methodology_notes}
          </div>
        </div>
      )}

      {data.key_findings && data.key_findings.length > 0 && (
        <div>
          <h4 style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 600 }}>
            Key Findings
          </h4>
          <div className="findings">
            {data.key_findings.map((f, i) => (
              <div key={i} className="finding-item positive">{f}</div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Thinking animation ────────────────────────────────── */

function ThinkingBubble() {
  return (
    <div className="message bot">
      <div className="msg-avatar bot">🧬</div>
      <div className="msg-body">
        <div className="thinking">
          <span />
          <span />
          <span />
        </div>
        <div className="loading-label">
          <Activity size={12} />
          Council deliberating… 4 agents analyzing in parallel
        </div>
      </div>
    </div>
  );
}
