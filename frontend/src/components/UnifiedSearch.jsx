import { useState, useRef, useEffect } from "react";
import { Search, BookOpen, FileText, ExternalLink, Code, Loader2, Upload, X, Check, FolderPlus } from "lucide-react";
import { unifiedSearch, ingestPapers, uploadPDF, getGraphStorages, createGraphStorage } from "../api";

const SOURCES = [
  { id: "all", label: "All Sources", icon: Search },
  { id: "arxiv", label: "arXiv", icon: FileText },
  { id: "pubmed", label: "PubMed", icon: BookOpen },
  // { id: "semantic_scholar", label: "Semantic Scholar", icon: BookOpen },
  { id: "paperswithcode", label: "Papers with Code", icon: Code },
];

export default function UnifiedSearch({ onClose, onIngest }) {
  const [query, setQuery] = useState("");
  const [selectedSources, setSelectedSources] = useState(["all"]);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedPapers, setSelectedPapers] = useState(new Set());
  const [uploading, setUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(null);
  const [graphStorages, setGraphStorages] = useState(["default"]);
  const [selectedGraphStorage, setSelectedGraphStorage] = useState("default");
  const [newGraphStorageName, setNewGraphStorageName] = useState("");
  const [showGraphStorageInput, setShowGraphStorageInput] = useState(false);
  const fileInputRef = useRef(null);

  // Load graph storages on mount
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

  const handleSourceToggle = (sourceId) => {
    if (sourceId === "all") {
      setSelectedSources(["all"]);
    } else {
      const newSources = selectedSources.filter((s) => s !== "all");
      if (newSources.includes(sourceId)) {
        setSelectedSources(newSources.filter((s) => s !== sourceId));
      } else {
        setSelectedSources([...newSources, sourceId]);
      }
      // Ensure "all" is not selected
      if (newSources.length > 0 && !newSources.includes("all")) {
        setSelectedSources([...newSources.filter((s) => s !== "all"), sourceId]);
      } else if (newSources.length === 0) {
        setSelectedSources([sourceId]);
      }
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setResults([]);
    setSelectedPapers(new Set());

    try {
      const sources = selectedSources.includes("all") ? ["all"] : selectedSources;
      const data = await unifiedSearch(query, sources);
      setResults(data.papers || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const togglePaper = (paperId) => {
    const newSelected = new Set(selectedPapers);
    if (newSelected.has(paperId)) {
      newSelected.delete(paperId);
    } else {
      newSelected.add(paperId);
    }
    setSelectedPapers(newSelected);
  };

  const handleIngest = async () => {
    if (selectedPapers.size === 0) return;

    setLoading(true);
    try {
      // Group papers by source
      const papersBySource = {};
      results.forEach((paper) => {
        if (selectedPapers.has(paper.id)) {
          if (!papersBySource[paper.source]) {
            papersBySource[paper.source] = [];
          }
          papersBySource[paper.source].push(paper);
        }
      });

      // Ingest based on source - use full IDs, not split
      for (const [source, papers] of Object.entries(papersBySource)) {
        if (source === "arxiv") {
          // Use arxiv ID format with id: prefix for exact match
          const arxivIds = papers.map((p) => `id:${p.id}`).join(" OR ");
          if (arxivIds) {
            await ingestPapers({ arxiv_query: arxivIds, max_results: papers.length, graph_storage: selectedGraphStorage });
          }
        } else if (source === "pubmed") {
          const pmids = papers.map((p) => `${p.id}[PMID]`).join(" OR ");
          if (pmids) {
            await ingestPapers({ pubmed_query: pmids, max_results: papers.length, graph_storage: selectedGraphStorage });
          }
        } else if (source === "paperswithcode") {
          // PapersWithCode uses semantic scholar IDs
          const paperIds = papers.map((p) => p.id).join(" OR ");
          if (paperIds) {
            await ingestPapers({ semantic_scholar_query: paperIds, max_results: papers.length, graph_storage: selectedGraphStorage });
          }
        } else if (source === "uploaded") {
          // Already ingested via upload
          continue;
        }
      }

      if (onIngest) {
        onIngest(selectedPapers.size);
      }
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setUploadSuccess(null);
    setError(null);

    try {
      const result = await uploadPDF(file);
      setUploadSuccess(result);
      // Add to results as a "local" paper
      const localPaper = {
        id: result.document_id,
        title: file.name,
        abstract: `Uploaded PDF (${result.text_length} chars, ${result.chunks_stored} chunks stored)`,
        authors: [],
        year: new Date().getFullYear(),
        source: "uploaded",
      };
      setResults((prev) => [...prev, localPaper]);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleCreateGraphStorage = async () => {
    if (!newGraphStorageName.trim()) return;
    try {
      await createGraphStorage(newGraphStorageName.trim());
      await loadGraphStorages();
      setSelectedGraphStorage(newGraphStorageName.trim());
      setNewGraphStorageName("");
      setShowGraphStorageInput(false);
    } catch (err) {
      setError(err.message);
    }
  };

  const getSourceIcon = (source) => {
    const sourceInfo = SOURCES.find((s) => s.id === source);
    return sourceInfo ? sourceInfo.icon : BookOpen;
  };

  return (
    <div className="unified-search-overlay">
      <div className="unified-search-modal">
        <div className="unified-search-header">
          <h2>
            <Search size={20} />
            Search Papers
          </h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        {/* Source Selection */}
        <div className="source-selection">
          <span className="source-label">Sources:</span>
          <div className="source-chips">
            {SOURCES.map((source) => {
              const Icon = source.icon;
              const isSelected = selectedSources.includes(source.id);
              return (
                <button
                  key={source.id}
                  className={`source-chip ${isSelected ? "selected" : ""}`}
                  onClick={() => handleSourceToggle(source.id)}
                >
                  <Icon size={14} />
                  {source.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Graph Storage Selection */}
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
            <button
              className="source-chip add-storage-btn"
              onClick={() => setShowGraphStorageInput(!showGraphStorageInput)}
            >
              <FolderPlus size={14} />
              New
            </button>
          </div>
        </div>
        {showGraphStorageInput && (
          <div className="new-storage-input">
            <input
              type="text"
              value={newGraphStorageName}
              onChange={(e) => setNewGraphStorageName(e.target.value)}
              placeholder="Enter storage name..."
              onKeyDown={(e) => e.key === "Enter" && handleCreateGraphStorage()}
            />
            <button onClick={handleCreateGraphStorage} disabled={!newGraphStorageName.trim()}>
              Create
            </button>
          </div>
        )}

        {/* PDF Upload */}
        <div className="upload-section">
          <span className="source-label">Or upload PDF:</span>
          <div className="upload-area">
            <input
              type="file"
              ref={fileInputRef}
              accept=".pdf"
              onChange={handleFileUpload}
              style={{ display: "none" }}
            />
            <button
              className="upload-btn"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
            >
              {uploading ? (
                <Loader2 size={16} className="spin" />
              ) : (
                <Upload size={16} />
              )}
              {uploading ? "Uploading..." : "Upload PDF"}
            </button>
            {uploadSuccess && (
              <span className="upload-success">
                <Check size={14} />
                Uploaded ({uploadSuccess.chunks_stored} chunks)
              </span>
            )}
          </div>
        </div>

        <form onSubmit={handleSearch} className="unified-search-form">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter search query (e.g., 'transformer neural networks')"
            className="unified-input"
          />
          <button type="submit" className="search-btn" disabled={loading || !query.trim()}>
            {loading ? <Loader2 size={16} className="spin" /> : <Search size={16} />}
            Search
          </button>
        </form>

        {error && (
          <div className="unified-error">
            {error}
          </div>
        )}

        <div className="unified-results">
          {results.length > 0 && (
            <div className="results-info">
              <span>{results.length} papers found</span>
              {selectedPapers.size > 0 && (
                <span className="selected-count">{selectedPapers.size} selected</span>
              )}
            </div>
          )}

          {results.map((paper) => {
            const SourceIcon = getSourceIcon(paper.source);
            return (
              <div
                key={paper.id}
                className={`paper-card ${selectedPapers.has(paper.id) ? "selected" : ""}`}
                onClick={() => togglePaper(paper.id)}
              >
                <div className="paper-checkbox">
                  <input
                    type="checkbox"
                    checked={selectedPapers.has(paper.id)}
                    onChange={() => togglePaper(paper.id)}
                  />
                </div>
                <div className="paper-content">
                  <div className="paper-header">
                    <h3 className="paper-title">{paper.title}</h3>
                    <span className={`source-badge source-${paper.source}`}>
                      <SourceIcon size={12} />
                      {paper.source}
                    </span>
                  </div>
                  <div className="paper-meta">
                    {paper.year && <span className="paper-year">{paper.year}</span>}
                    {paper.venue && <span className="paper-venue">{paper.venue}</span>}
                    {paper.citation_count != null && (
                      <span className="paper-citations">{paper.citation_count} citations</span>
                    )}
                  </div>
                  {paper.authors.length > 0 && (
                    <div className="paper-authors">
                      {paper.authors.slice(0, 3).join(", ")}
                      {paper.authors.length > 3 && ` +${paper.authors.length - 3} more`}
                    </div>
                  )}
                  {paper.abstract && (
                    <p className="paper-abstract">
                      {paper.abstract.length > 200
                        ? paper.abstract.slice(0, 200) + "..."
                        : paper.abstract}
                    </p>
                  )}
                  <div className="paper-links">
                    {paper.pdf_url && (
                      <a
                        href={paper.pdf_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="paper-link"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <FileText size={12} /> PDF
                      </a>
                    )}
                    {paper.code_url && (
                      <a
                        href={paper.code_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="paper-link"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <Code size={12} /> Code
                      </a>
                    )}
                    {paper.doi && (
                      <a
                        href={`https://doi.org/${paper.doi}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="paper-link"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <ExternalLink size={12} /> DOI
                      </a>
                    )}
                  </div>
                </div>
              </div>
            );
          })}

          {loading && (
            <div className="unified-loading">
              <Loader2 size={24} className="spin" />
              <span>Searching across sources...</span>
            </div>
          )}

          {!loading && results.length === 0 && query && !error && (
            <div className="unified-empty">
              <Search size={32} />
              <p>No papers found. Try a different search query.</p>
            </div>
          )}
        </div>

        {selectedPapers.size > 0 && (
          <div className="unified-actions">
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
