import { useState } from "react";
import { Search, BookOpen, ExternalLink, Loader2 } from "lucide-react";
import { searchPubMed, ingestPapers } from "../api";

export default function PubMedSearch({ onClose, onIngest }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedPapers, setSelectedPapers] = useState(new Set());

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setResults([]);
    setSelectedPapers(new Set());

    try {
      const data = await searchPubMed(query);
      setResults(data.papers || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const togglePaper = (pmid) => {
    const newSelected = new Set(selectedPapers);
    if (newSelected.has(pmid)) {
      newSelected.delete(pmid);
    } else {
      newSelected.add(pmid);
    }
    setSelectedPapers(newSelected);
  };

  const handleIngest = async () => {
    if (selectedPapers.size === 0) return;

    setLoading(true);
    try {
      // Create a combined query from selected papers' PMIDs
      const pmidList = Array.from(selectedPapers).join(" OR ");
      const pmids = Array.from(selectedPapers);
      
      // Use ingest endpoint with pubmed_query for selected PMIDs
      const pubmedQuery = pmids.map(pmid => `${pmid}[PMID]`).join(" OR ");
      
      await ingestPapers({ pubmed_query: pubmedQuery, max_results: pmids.length });
      
      if (onIngest) {
        onIngest(pmids.length);
      }
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="pubmed-search-overlay">
      <div className="pubmed-search-modal">
        <div className="pubmed-search-header">
          <h2>
            <Search size={20} />
            Search PubMed
          </h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <form onSubmit={handleSearch} className="pubmed-search-form">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter search query (e.g., 'BRCA1 cancer')"
            className="pubmed-input"
          />
          <button type="submit" className="search-btn" disabled={loading || !query.trim()}>
            {loading ? <Loader2 size={16} className="spin" /> : <Search size={16} />}
            Search
          </button>
        </form>

        {error && (
          <div className="pubmed-error">
            {error}
          </div>
        )}

        <div className="pubmed-results">
          {results.length > 0 && (
            <div className="results-info">
              <span>{results.length} papers found</span>
              {selectedPapers.size > 0 && (
                <span className="selected-count">{selectedPapers.size} selected</span>
              )}
            </div>
          )}
          
          {results.map((paper) => (
            <div
              key={paper.pmid}
              className={`paper-card ${selectedPapers.has(paper.pmid) ? "selected" : ""}`}
              onClick={() => togglePaper(paper.pmid)}
            >
              <div className="paper-checkbox">
                <input
                  type="checkbox"
                  checked={selectedPapers.has(paper.pmid)}
                  onChange={() => togglePaper(paper.pmid)}
                />
              </div>
              <div className="paper-content">
                <h3 className="paper-title">{paper.title}</h3>
                <div className="paper-meta">
                  <span className="paper-pmid">PMID: {paper.pmid}</span>
                  {paper.year && <span className="paper-year">{paper.year}</span>}
                  {paper.journal && <span className="paper-journal">{paper.journal}</span>}
                </div>
                {paper.authors.length > 0 && (
                  <div className="paper-authors">
                    {paper.authors.slice(0, 3).join(", ")}
                    {paper.authors.length > 3 && ` +${paper.authors.length - 3} more`}
                  </div>
                )}
                {paper.abstract && (
                  <p className="paper-abstract">
                    {paper.abstract.length > 300 
                      ? paper.abstract.slice(0, 300) + "..." 
                      : paper.abstract}
                  </p>
                )}
                {paper.doi && (
                  <a 
                    href={`https://doi.org/${paper.doi}`} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="paper-doi"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <ExternalLink size={12} />
                    DOI: {paper.doi}
                  </a>
                )}
              </div>
            </div>
          ))}
          
          {loading && (
            <div className="pubmed-loading">
              <Loader2 size={24} className="spin" />
              <span>Searching PubMed...</span>
            </div>
          )}

          {!loading && results.length === 0 && query && !error && (
            <div className="pubmed-empty">
              <BookOpen size={32} />
              <p>No papers found. Try a different search query.</p>
            </div>
          )}
        </div>

        {selectedPapers.size > 0 && (
          <div className="pubmed-actions">
            <button 
              className="ingest-btn" 
              onClick={handleIngest}
              disabled={loading}
            >
              {loading ? (
                <>
                  <Loader2 size={16} className="spin" />
                  Ingesting...
                </>
              ) : (
                <>
                  <BookOpen size={16} />
                  Ingest {selectedPapers.size} paper{selectedPapers.size > 1 ? "s" : ""} to Knowledge Base
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
