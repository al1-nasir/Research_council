const API_BASE = "/api";

export async function sendQuery(query, graphStorage = "default") {
  const resp = await fetch(`${API_BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, graph_storage: graphStorage }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(err.detail || "Query failed");
  }
  return resp.json();
}

export async function ingestPapers({ pubmed_query, arxiv_query, semantic_scholar_query, max_results = 20, graph_storage = "default" }) {
  const resp = await fetch(`${API_BASE}/ingest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pubmed_query, arxiv_query, semantic_scholar_query, max_results, graph_storage }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(err.detail || "Ingestion failed");
  }
  return resp.json();
}

export async function fetchGraph(entityName = null, label = "Paper", limit = 50, graphStorage = "default") {
  const params = new URLSearchParams({ label, limit, graph_storage: graphStorage });
  if (entityName) params.set("entity_name", entityName);
  const resp = await fetch(`${API_BASE}/graph?${params}`);
  if (!resp.ok) throw new Error("Graph fetch failed");
  return resp.json();
}

export async function healthCheck() {
  try {
    const resp = await fetch(`${API_BASE}/health`);
    return resp.ok;
  } catch {
    return false;
  }
}

export async function searchPubMed(query, maxResults = 20) {
  const resp = await fetch(`${API_BASE}/pubmed/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, max_results: maxResults }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(err.detail || "PubMed search failed");
  }
  return resp.json();
}

export async function fetchPapers(limit = 100, skip = 0, graphStorage = "default") {
  const params = new URLSearchParams({ limit, skip, graph_storage: graphStorage });
  const resp = await fetch(`${API_BASE}/papers?${params}`);
  if (!resp.ok) throw new Error("Failed to fetch papers");
  return resp.json();
}

export async function unifiedSearch(query, sources = ["all"], maxResults = 20) {
  const resp = await fetch(`${API_BASE}/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, sources, max_results: maxResults }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(err.detail || "Search failed");
  }
  return resp.json();
}

export async function uploadPDF(file) {
  const formData = new FormData();
  formData.append("file", file);
  
  const resp = await fetch(`${API_BASE}/upload`, {
    method: "POST",
    body: formData,
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(err.detail || "Upload failed");
  }
  return resp.json();
}

export async function getGraphStorages() {
  const resp = await fetch(`${API_BASE}/graph/storages`);
  if (!resp.ok) throw new Error("Failed to fetch graph storages");
  return resp.json();
}

export async function createGraphStorage(name) {
  const resp = await fetch(`${API_BASE}/graph/storages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(err.detail || "Failed to create graph storage");
  }
  return resp.json();
}

export async function deleteGraphStorage(name) {
  const resp = await fetch(`${API_BASE}/graph/storages/${encodeURIComponent(name)}`, {
    method: "DELETE",
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(err.detail || "Failed to delete graph storage");
  }
  return resp.json();
}

export async function removePaperFromGraph(paperId, graphStorage = "default") {
  const resp = await fetch(`${API_BASE}/graph/papers/${encodeURIComponent(paperId)}`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ graph_storage: graphStorage }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(err.detail || "Failed to remove paper from graph");
  }
  return resp.json();
}
