# 🧬 Research Council

**Agentic AI for scientific research** — connects knowledge across thousands of
papers using a Knowledge Graph (GraphRAG) and a Multi-LLM Council that
deliberates to produce trustworthy, cited, confidence-scored answers.

## Quick Start

```bash
# 1. Clone & enter
cd research-council

# 2. Create virtual environment
uv venv && source .venv/bin/activate

# 3. Install dependencies
uv sync

# 4. Copy env and add your keys
cp .env.example .env
# edit .env with your GROQ_API_KEY and OPENROUTER_API_KEY

# 5. Start Neo4j (Docker)
docker run -d --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:5-community

# 6. Run the API
uvicorn api.main:app --reload --port 8000
```

## Architecture

```
User Query → FastAPI → LangGraph Orchestrator
  → bigtool dynamic tool selection (2-4 tools, not all)
  → Neo4j graph queries + ChromaDB vector search
  → Multi-LLM Council (4 agents via Groq, parallel async)
  → Chairman synthesis (OpenRouter, best model)
  → Confidence-scored answer with provenance
  → Conclusion written back to knowledge graph
```

## Hardware Requirements

- **RAM:** 16 GB system memory
- **VRAM:** 4 GB GPU (optional — all embeddings run on CPU)
- **LLM inference:** Groq + OpenRouter APIs (no local models required)
# Research_council
