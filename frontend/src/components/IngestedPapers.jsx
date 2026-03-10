import { useState, useEffect } from "react";
import { X, ExternalLink, BookOpen, Loader2, Trash2, FolderPlus } from "lucide-react";
import { fetchPapers, getGraphStorages, removePaperFromGraph } from "../api";

export default function IngestedPapers({ onClose }) {
  const [papers, setPapers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [graphStorages, setGraphStorages] = useState(["default"]);
  const [selectedGraphStorage, setSelectedGraphStorage] = useState("default");
  const [removing, setRemoving] = useState(null);

  useEffect(() => {
    loadGraphStorages();
    loadPapers();
  }, []);

  // Reload papers when graph storage changes
  useEffect(() => {
    loadPapers();
  }, [selectedGraphStorage]);

  const loadGraphStorages = async () => {
    try {
      const storages = await getGraphStorages();
      setGraphStorages(storages && storages.length > 0 ? storages : ["default"]);
    } catch (err) {
      console.error("Failed to load graph storages:", err);
      setGraphStorages(["default"]);
    }
  };

  const loadPapers = async () => {
    setLoading(true);
    try {
      const data = await fetchPapers(100, 0, selectedGraphStorage);
      setPapers(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRemovePaper = async (paperId) => {
    if (!confirm("Are you sure you want to remove this paper from the graph?")) return;
    
    setRemoving(paperId);
    try {
      await removePaperFromGraph(paperId, selectedGraphStorage);
      await loadPapers();
    } catch (err) {
      setError(err.message);
    } finally {
      setRemoving(null);
    }
  };

  return (
    <div className="papers-overlay">
      <div className="papers-modal">
        <div className="papers-header">
          <h2>
            <BookOpen size={20} />
            Ingested Papers ({papers.length})
          </h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        {/* Graph Storage Selector */}
        <div className="source-selection">
          <span className="source-label">Graph Storage:</span>
          <div className="source-chips">
            {graphStorages.map((storage) => (
              <button
                key={storage}
                className={`source-chip ${selectedGraphStorage === storage ? "selected" : ""}`}
                onClick={() => setSelectedGraphStorage(storage)}
              >
                <FolderPlus size={14} />
                {storage}
              </button>
            ))}
          </div>
        </div>

        <div className="papers-content">
          {loading && (
            <div className="papers-loading">
              <Loader2 size={24} className="spin" />
              <span>Loading papers...</span>
            </div>
          )}

          {error && (
            <div className="papers-error">
              {error}
            </div>
          )}

          {!loading && !error && papers.length === 0 && (
            <div className="papers-empty">
              <BookOpen size={32} />
              <p>No papers ingested yet.</p>
              <p className="hint">Use "Search PubMed" to find and ingest papers.</p>
            </div>
          )}

          {!loading && !error && papers.length > 0 && (
            <div className="papers-list">
              {papers.map((paper, i) => (
                <div key={i} className="paper-item">
                  <div className="paper-info">
                    <h3 className="paper-title">{paper.title}</h3>
                    <div className="paper-meta">
                      <span className="paper-pmid">PMID: {paper.pmid}</span>
                      {paper.year && <span className="paper-year">{paper.year}</span>}
                    </div>
                    {paper.journal && (
                      <div className="paper-journal">{paper.journal}</div>
                    )}
                    {paper.authors && paper.authors.length > 0 && (
                      <div className="paper-authors">
                        {paper.authors.slice(0, 3).join(", ")}
                        {paper.authors.length > 3 && ` +${paper.authors.length - 3} more`}
                      </div>
                    )}
                  </div>
                  <div className="paper-actions">
                    <button 
                      className="paper-link remove-btn"
                      onClick={() => handleRemovePaper(paper.pmid || paper.id)}
                      disabled={removing === (paper.pmid || paper.id)}
                      title="Remove from graph"
                    >
                      {removing === (paper.pmid || paper.id) ? (
                        <Loader2 size={16} className="spin" />
                      ) : (
                        <Trash2 size={16} />
                      )}
                    </button>
                    {paper.doi && (
                      <a 
                        href={`https://doi.org/${paper.doi}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="paper-link"
                        title="Open DOI"
                      >
                        <ExternalLink size={16} />
                      </a>
                    )}
                    <a 
                      href={`https://pubmed.ncbi.nlm.nih.gov/${paper.pmid}/`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="paper-link"
                      title="View on PubMed"
                    >
                      PubMed
                    </a>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
