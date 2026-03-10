export default function EvidenceTrail({ citations, keyFindings, contradictions }) {
  return (
    <div>
      {/* Key findings */}
      {keyFindings && keyFindings.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <h4 style={{ fontSize: 12, fontWeight: 600, color: "var(--text-muted)", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.05em" }}>
            Key Findings
          </h4>
          <div className="findings">
            {keyFindings.map((f, i) => (
              <div key={i} className="finding-item positive">
                {f}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Contradictions */}
      {contradictions && contradictions.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <h4 style={{ fontSize: 12, fontWeight: 600, color: "var(--text-muted)", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.05em" }}>
            Contradictions Found
          </h4>
          <div className="findings">
            {contradictions.map((c, i) => (
              <div key={i} className="finding-item negative">
                {c}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Citations */}
      {citations && citations.length > 0 && (
        <div>
          <h4 style={{ fontSize: 12, fontWeight: 600, color: "var(--text-muted)", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.05em" }}>
            Citations
          </h4>
          <div className="citations-list">
            {citations.map((c, i) => (
              <div key={i} className="citation-item">
                <span className="citation-idx">{i + 1}</span>
                <span className="citation-claim">{c.claim}</span>
                <span className="citation-paper" title={c.paper_title}>
                  {c.paper_id || "—"}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {(!citations || citations.length === 0) &&
       (!keyFindings || keyFindings.length === 0) &&
       (!contradictions || contradictions.length === 0) && (
        <p style={{ color: "var(--text-muted)", fontSize: 13 }}>
          No evidence trail available for this response.
        </p>
      )}
    </div>
  );
}
