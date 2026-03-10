# 🧬 Research Council - Technical Report

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Architecture](#system-architecture)
3. [Core Features](#core-features)
   - [Graph RAG (Knowledge Graph-based Retrieval)](#graph-rag-knowledge-graph-based-retrieval)
   - [Multi-Agent LLM Council](#multi-agent-llm-council)
   - [Dynamic Tool Selection (BigTool Agent)](#dynamic-tool-selection-bigtool-agent)
   - [Hybrid Retrieval System](#hybrid-retrieval-system)
   - [Graph Storage Management](#graph-storage-management)
4. [Technical Implementation Details](#technical-implementation-details)
   - [Knowledge Graph Builder](#knowledge-graph-builder)
   - [Entity Extraction Pipeline](#entity-extraction-pipeline)
   - [Graph Schema and Data Model](#graph-schema-and-data-model)
   - [Vector Embedding Pipeline](#vector-embedding-pipeline)
5. [Multi-Agent Council System](#multi-agent-council-system)
   - [Agent Definitions and Roles](#agent-definitions-and-roles)
   - [Three-Stage Deliberation Process](#three-stage-deliberation-process)
   - [Chairman Synthesis](#chairman-synthesis)
   - [Confidence Scoring and Citations](#confidence-scoring-and-citations)
6. [Orchestration and Flow](#orchestration-and-flow)
   - [LangGraph State Management](#langgraph-state-management)
   - [Research Pipeline](#research-pipeline)
   - [Tool Registry and Execution](#tool-registry-and-execution)
7. [Data Ingestion Pipeline](#data-ingestion-pipeline)
   - [Paper Sources](#paper-sources)
   - [Text Chunking](#text-chunking)
   - [Embedding Storage](#embedding-storage)
8. [API Endpoints](#api-endpoints)
9. [Frontend Interface](#frontend-interface)
10. [Configuration and Deployment](#configuration-and-deployment)
11. [Hardware and Performance Requirements](#hardware-and-performance-requirements)
12. [Future Enhancements](#future-enhancements)

---

## Executive Summary

**Research Council** is an agentic AI system for scientific research that combines two powerful paradigms: **Graph-based Retrieval Augmented Generation (GraphRAG)** and a **Multi-LLM Council** that deliberates to produce trustworthy, confidence-scored, and fully-cited answers to biomedical research questions.

The system connects knowledge across thousands of scientific papers using a Neo4j-powered knowledge graph, enabling sophisticated queries that traditional RAG systems cannot answer—such as finding paths between entities, identifying contradictions, and discovering non-obvious connections between drugs, genes, diseases, and pathways.

At its core, Research Council employs a novel **Multi-Agent Council** architecture where four specialized AI agents (Evidence Analyst, Scientific Skeptic, Knowledge Connector, and Methodology Expert) analyze research questions in parallel, cross-review each other's conclusions, and synthesize their findings through an authoritative Chairman agent.

---

## System Architecture

The Research Council system follows a modular, service-oriented architecture:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (React)                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ Query Input │  │Council View│  │Graph Viewer │  │ Evidence Trail      │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │ HTTP/REST
┌────────────────────────────────▼────────────────────────────────────────────┐
│                          FASTAPI BACKEND                                     │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                          LangGraph Orchestrator                        │  │
│  │  ┌──────────────┐  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  │  │
│  │  │Select Tools │  │ Retrieve   │  │Assemble     │  │ Council     │  │  │
│  │  │(BigTool)    │  │(Hybrid)    │  │Context      │  │(Multi-Agent)│  │  │
│  │  └──────────────┘  └─────────────┘  └──────────────┘  └─────────────┘  │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
└──────────┬───────────────────────┬───────────────────────┬──────────────────┘
           │                       │                       │
┌──────────▼───────────┐ ┌────────▼────────┐ ┌────────────▼───────────────┐
│   Neo4j Graph DB    │ │  ChromaDB       │ │  External APIs              │
│  - Paper nodes      │ │  (Embeddings)   │ │  - PubMed                  │
│  - Entity nodes     │ │  - Paper chunks │ │  - arXiv                   │
│  - Relationships    │ │  - Tool desc.   │ │  - Semantic Scholar        │
│  - Conclusions      │ │                 │ │  - Papers With Code        │
└────────────────────┘ └──────────────────┘ └────────────────────────────┘
```

### Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | React + Vite | User interface with chat, graph visualization, evidence trails |
| **API** | FastAPI | REST endpoints for queries, ingestion, graph exploration |
| **Orchestration** | LangGraph | State management and pipeline execution |
| **Knowledge Graph** | Neo4j | Graph database for entities, papers, relationships |
| **Vector Store** | ChromaDB | Semantic search embeddings (CPU-based) |
| **LLM Inference** | Groq + OpenRouter | Fast inference for agents and entity extraction |
| **Embeddings** | SentenceTransformers (MiniLM) | CPU-only text embedding |
| **Observability** | Langfuse | LLM call tracing and monitoring |

---

## Core Features

### Graph RAG (Knowledge Graph-based Retrieval)

Graph RAG represents a paradigm shift from traditional vector-based RAG systems. Instead of relying solely on semantic similarity, Research Council builds and queries a **rich knowledge graph** that captures the relationships between biomedical entities.

#### Key Capabilities:

1. **Entity-Centric Retrieval**: Query not just papers, but specific entities (genes, drugs, diseases, proteins, pathways) and their relationships
2. **Path Finding**: Discover how two entities are connected through intermediate nodes (drug → protein → pathway → disease)
3. **Contradiction Detection**: Identify papers that contradict each other
4. **Supporting Evidence**: Find papers that support or confirm other papers' findings
5. **Multi-Hop Reasoning**: Navigate through multiple relationship types to answer complex queries

#### How Graph RAG Works:

```
Traditional RAG:                    Graph RAG:
┌──────────┐                        ┌──────────┐
│  Query  │                        │  Query  │
└────┬─────┘                        └────┬─────┘
     │                                   │
     ▼                                   ▼
┌──────────┐                        ┌──────────┐
│ Vector   │                        │ Hybrid   │
│ Search   │                        │ Retrieval│
└────┬─────┘                        └────┬─────┘
     │                                   │
     ▼                                   ▼
┌──────────┐                        ┌──────────┐
│ Top      │                        │ Vector   │
│ Chunks   │                        │ Search   │
└──────────┘                        └────┬─────┘
                                         │
                                         ▼
                                  ┌──────────┐
                                  │ Graph    │
                                  │ Expansion│
                                  └────┬─────┘
                                       │
                                       ▼
                                  ┌──────────┐
                                  │ Rich     │
                                  │ Context  │
                                  └──────────┘
```

The hybrid approach combines:
- **Vector search** (ChromaDB): Fast semantic similarity over paper chunks
- **Graph expansion** (Neo4j): Fetch entity neighborhoods from identified papers
- **Context assembly**: Merge both sources into a compact, ~2,000 token context

---

### Multi-Agent LLM Council

The Council is the heart of Research Council's deliberative reasoning. Instead of relying on a single LLM to answer questions, the system employs **four specialized agents** that analyze questions from different perspectives, followed by a **Chairman** that synthesizes their conclusions.

#### The Four Specialist Agents:

| Agent | Role | Focus | Color |
|-------|------|-------|-------|
| **🔬 Evidence Agent** | Evidence Analyst | Summarizes what the evidence actually shows, with precision about sample sizes, study types, effect sizes | `#00d2a0` (Teal) |
| **⚔️ Skeptic Agent** | Scientific Skeptic | Finds weaknesses: biased designs, underpowered samples, conflicting results, publication bias | `#ff6b6b` (Red) |
| **🔗 Connector Agent** | Knowledge Connector | Finds non-obvious links: drug repurposing, analogous mechanisms, cross-domain techniques | `#4da6ff` (Blue) |
| **📋 Methodology Agent** | Research Methodology | Evaluates experimental designs, controls, statistical methods, justification of conclusions | `#ffa94d` (Orange) |

#### Why a Multi-Agent Council?

1. **Reduced Bias**: Different agents catch different types of errors
2. **Comprehensive Analysis**: Multiple perspectives lead to more robust conclusions
3. **Cross-Verification**: Agents critique each other, catching mistakes
4. **Confidence Calibration**: Agreement/disagreement between agents informs confidence scores
5. **Traceability**: Each claim can be traced back to a specific agent's analysis

---

### Dynamic Tool Selection (BigTool Agent)

Research Council uses a novel **BigTool** approach for dynamic tool selection. Instead of passing all available tools to an LLM (which would waste context tokens and confuse the model), the system:

1. **Indexes all tools** with semantic embeddings at startup
2. **Searches for relevant tools** when a query arrives
3. **Selects only 2-4 tools** most relevant to the current query

This approach ensures:
- Token efficiency (no bloated tool schemas in prompts)
- Relevance (tools matched to query semantics)
- Scalability (can handle 50+ tools without degradation)

#### Available Tool Categories:

- **Graph Tools**: Query entities, find paths, get neighbors, find contradictions, find supporting papers
- **Paper Tools**: Search papers, get metadata, fetch abstracts
- **Evidence Tools**: Extract evidence, compare findings, assess quality

---

### Hybrid Retrieval System

The hybrid retrieval system combines two complementary approaches:

#### 1. Vector Search (ChromaDB)
- Embeds paper chunks using MiniLM (384-dimensional vectors)
- Searches for semantic similarity to the query
- Returns top-k most relevant chunks

#### 2. Graph Expansion (Neo4j)
- Takes identified papers from vector search
- Fetches their entity neighborhoods from the graph
- Expands context with relationship information

#### Assembly Process:
```python
# 1. Vector search returns top chunks
chunks = vector_search(query, n_results=5)

# 2. Extract unique paper IDs
paper_ids = [c["source_id"] for c in chunks]

# 3. For each paper, fetch graph context
for paper_id in paper_ids[:5]:
    graph_context = query_paper_neighbors(paper_id)

# 4. Merge into compact context (~2000 tokens)
context = assemble_context(chunks, graph_context)
```

---

### Graph Storage Management

Research Council supports **multiple isolated graph storages**, enabling:

- **Multi-tenant scenarios**: Different users or projects can have separate graphs
- **Topic separation**: Research on different diseases/drugs in isolated environments
- **Experimental workspaces**: Test changes without affecting production data

Features:
- Create new graph storages
- List available storages
- Delete storages (with all papers)
- Switch between storages in the UI

---

## Technical Implementation Details

### Knowledge Graph Builder

The knowledge graph builder ([`graph/kg_builder.py`](graph/kg_builder.py)) handles:

1. **Paper Node Creation**: Creates or updates Paper nodes with metadata
2. **Entity Extraction**: Uses LLM to extract biomedical entities from paper abstracts
3. **Relationship Writing**: Writes extracted relationships to the graph

#### Entity Types Extracted:

| Entity Type | Properties | Example |
|-------------|------------|---------|
| **Gene** | name, symbol | TP53, BRCA1 |
| **Drug** | name, mechanism | imatinib, metformin |
| **Disease** | name | breast cancer, Alzheimer's |
| **Protein** | name, function | p53, BRCA1 |
| **Pathway** | name | MAPK signaling |

#### Relationship Types:

| Relationship | Meaning | Example |
|--------------|---------|---------|
| **MENTIONS** | Paper mentions entity | Paper → Gene |
| **STUDIES** | Paper studies disease | Paper → Disease |
| **TARGETS** | Drug targets protein | Drug → Protein |
| **INVOLVED_IN** | Gene in pathway | Gene → Pathway |
| **CONTRADICTS** | Paper contradicts paper | Paper ↔ Paper |
| **SUPPORTS** | Paper supports paper | Paper ↔ Paper |
| **CITES** | Paper cites paper | Paper → Paper |
| **AUTHORED_BY** | Paper authored by author | Paper → Author |

---

### Entity Extraction Pipeline

The entity extraction uses **OpenRouter (GPT-4o-mini)** to analyze paper abstracts and extract structured entities:

```python
EXTRACTION_SYSTEM_PROMPT = """You are a biomedical entity extractor. Given a paper's 
title and abstract, extract the following entities and relationships as JSON:

{
  "genes": [{"name": "...", "symbol": "..."}],
  "drugs": [{"name": "...", "mechanism": "..."}],
  "diseases": [{"name": "..."}],
  "proteins": [{"name": "...", "function": "..."}],
  "pathways": [{"name": "..."}],
  "relationships": [
    {"source_type": "Drug", "source": "...", "rel": "TARGETS", 
     "target_type": "Protein", "target": "..."}
  ]
}
"""
```

Key features:
- **Retry logic**: Uses Tenacity for exponential backoff on failures
- **JSON parsing**: Strips markdown code fences, handles parsing errors gracefully
- **Parameterized queries**: All Neo4j writes use parameterized Cypher (no injection)

---

### Graph Schema and Data Model

The schema ([`graph/schema.py`](graph/schema.py)) defines:

#### Node Labels:
- `Paper` - Scientific publications
- `Gene` - Genetic entities
- `Drug` - Pharmaceutical compounds
- `Disease` - Medical conditions
- `Protein` - Protein entities
- `Pathway` - Biological pathways
- `Author` - Research authors
- `Conclusion` - Generated research conclusions

#### Constraints (Unique IDs):
```cypher
CREATE CONSTRAINT FOR (p:Paper) REQUIRE p.id IS UNIQUE
CREATE CONSTRAINT FOR (g:Gene) REQUIRE g.symbol IS UNIQUE
CREATE CONSTRAINT FOR (d:Drug) REQUIRE d.name IS UNIQUE
CREATE CONSTRAINT FOR (ds:Disease) REQUIRE ds.name IS UNIQUE
CREATE CONSTRAINT FOR (pr:Protein) REQUIRE pr.uniprot_id IS UNIQUE
CREATE CONSTRAINT FOR (pw:Pathway) REQUIRE pw.kegg_id IS UNIQUE
CREATE CONSTRAINT FOR (a:Author) REQUIRE a.name IS UNIQUE
CREATE CONSTRAINT FOR (c:Conclusion) REQUIRE c.id IS UNIQUE
```

#### Indexes:
```cypher
CREATE INDEX FOR (p:Paper) ON (p.title)
CREATE INDEX FOR (p:Paper) ON (p.year)
CREATE INDEX FOR (p:Paper) ON (p.doi)
```

---

### Vector Embedding Pipeline

The embedding pipeline ([`ingestion/embedding_pipeline.py`](ingestion/embedding_pipeline.py)):

1. **Model**: SentenceTransformers with `all-MiniLM-L6-v2` (384 dimensions)
2. **Device**: CPU-only (preserves GPU VRAM for other tasks)
3. **Batching**: Batch encoding for performance (32 items per batch)
4. **Storage**: ChromaDB with persistent storage

#### Storage Flow:
```python
# 1. Chunk text
chunks = chunk_text(abstract, source_id=pmid)

# 2. Embed chunks
embeddings = embed_texts([c.text for c in chunks])

# 3. Store in ChromaDB
collection.upsert(
    ids=[f"{pmid}__chunk_{i}" for i in range(len(chunks))],
    documents=[c.text for c in chunks],
    embeddings=embeddings,
    metadatas=[{"source_id": pmid, "chunk_index": i} for i in range(len(chunks))]
)
```

---

## Multi-Agent Council System

### Agent Definitions and Roles

Each agent has a distinct system prompt that defines its role:

#### Evidence Agent
```python
system_prompt="You are a rigorous evidence analyst reviewing scientific literature. 
Given a knowledge graph subgraph and paper abstracts, summarize what the evidence 
actually shows. Be precise about sample sizes, study types, and effect sizes. 
Never speculate beyond what the data shows."
```

#### Skeptic Agent
```python
system_prompt="You are a critical reviewer. Your job is to find weaknesses: 
biased study designs, underpowered samples, conflicting results, publication bias, 
or methodological flaws. Be constructively critical, not dismissive."
```

#### Connector Agent
```python
system_prompt="You are a cross-domain knowledge connector. Find non-obvious links 
between concepts in the graph — drug repurposing opportunities, analogous mechanisms 
from other diseases, or techniques from adjacent fields that apply here."
```

#### Methodology Agent
```python
system_prompt="You evaluate research methodology. Assess whether experimental designs 
are appropriate, controls are adequate, statistical methods are sound, and whether 
conclusions are justified by the methods used."
```

#### Chairman Agent
```python
system_prompt="You are the Chairman of a research council. You receive responses from 
4 specialist agents and their cross-reviews. Synthesize them into a single authoritative 
answer. Assign a confidence score (0.0–1.0). Every claim must cite a specific paper node 
from the knowledge graph. Format your response as JSON..."
```

---

### Three-Stage Deliberation Process

The council operates in three distinct stages:

#### Stage 1: Independent Opinions (Parallel)

All four specialist agents receive the same context and query, but analyze it independently:

```
Query: "What is the evidence for metformin in glioblastoma treatment?"

┌─────────────────────────────────────────────────────────────────┐
│                    PARALLEL EXECUTION                           │
├─────────────────┬─────────────────┬─────────────────┬──────────┤
│   Evidence      │    Skeptic      │   Connector    │Methodology│
│   Agent         │    Agent        │    Agent        │  Agent   │
├─────────────────┼─────────────────┼─────────────────┼──────────┤
│ Summarizes      │ Identifies      │ Finds non-      │ Evaluates│
│ what evidence   │ weaknesses,      │ obvious links  │ research │
│ shows with      │ biases,          │ (drug repur-    │ methods  │
│ precision       │ underpowered    │ posing, cross- │          │
│                 │ samples          │ domain)         │          │
└─────────────────┴─────────────────┴─────────────────┴──────────┘
         │                 │                 │                 │
         ▼                 ▼                 ▼                 ▼
    Response 1      Response 2        Response 3        Response 4
```

**Implementation**: Uses `asyncio.gather()` to run all agents in parallel for speed.

---

#### Stage 2: Cross-Review (Peer Evaluation)

Each agent reviews ALL OTHER agents' responses (anonymized):

```
Agent 1 reviews Agent 2, 3, 4
Agent 2 reviews Agent 1, 3, 4
Agent 3 reviews Agent 1, 2, 4
Agent 4 reviews Agent 1, 2, 3

Total: 12 cross-reviews (4 × 3)
```

For each review, the agent:
- Rates agreement (0.0 = disagree, 1.0 = fully agree)
- Provides constructive critique
- Lists key points

**Implementation**: Runs in small batches to avoid rate limiting.

---

#### Stage 3: Chairman Synthesis

The Chairman receives:
1. All four original agent responses
2. All twelve cross-reviews
3. List of available paper IDs for citation

The Chairman produces a final synthesis with:
- **Summary**: Authoritative answer to the query
- **Confidence Score**: 0.0-1.0 based on evidence quality and agent agreement
- **Key Findings**: List of major discoveries
- **Contradictions**: Any conflicts identified
- **Citations**: Specific paper references for each claim
- **Methodology Notes**: Assessment of research quality
- **Agent Agreement**: How much agents agreed (0.0-1.0)

---

### Confidence Scoring and Citations

The confidence scoring algorithm considers:

1. **Evidence Quality**: How strong is the supporting evidence?
2. **Agent Agreement**: Do agents agree? (High agreement → higher confidence)
3. **Methodology**: Are studies well-designed?
4. **Contradictions**: Are there conflicting papers?

#### Citation Format:
```json
{
  "claim": "Metformin shows anti-tumor effects in glioblastoma",
  "paper_id": "PMID:12345678",
  "paper_title": "Metformin inhibits glioblastoma cell proliferation...",
  "confidence": 0.85
}
```

Every claim in the final answer MUST cite a specific paper node from the knowledge graph.

---

## Orchestration and Flow

### LangGraph State Management

The system uses LangGraph's StateGraph to orchestrate the research pipeline:

#### State Schema ([`orchestrator/state.py`](orchestrator/state.py)):
```python
class ResearchState(TypedDict):
    # Input
    query: str
    
    # Tool selection
    selected_tools: list[dict]
    
    # Retrieval
    chunks: list[dict]
    graph_context: list[dict]
    paper_ids: list[str]
    
    # Assembled context
    context: str
    
    # Council
    stage1_responses: list[AgentResponse]
    stage2_reviews: list[CrossReview]
    synthesis: ChairmanSynthesis
    
    # Output
    council_result: CouncilResult
    conclusion_id: str
    
    # Metadata
    total_tokens: int
    error: str | None
```

---

### Research Pipeline

The complete pipeline flows through these nodes:

```
┌───────────────┐     ┌────────────┐     ┌─────────────────┐
│ select_tools  │────▶│  retrieve  │────▶│ assemble_context│
│   (BigTool)   │     │  (Hybrid)  │     │  (~2000 tokens) │
└───────────────┘     └────────────┘     └────────┬────────┘
                                                   │
                                                   ▼
┌───────────────┐     ┌────────────┐     ┌─────────────────┐
│   writeback   │◀────│  council   │◀────│                 │
│   (to Neo4j)  │     │(Multi-Agent)│     │                 │
└───────────────┘     └────────────┘     └─────────────────┘
```

#### Node Functions:

1. **`node_select_tools`**: Uses BigTool to find 2-4 relevant tools
2. **`node_retrieve`**: Runs hybrid retrieval (vector + graph)
3. **`node_assemble_context`**: Merges chunks + graph facts into ~2000 tokens
4. **`node_council`**: Runs full 3-stage deliberation
5. **`node_writeback`**: Writes conclusion to Neo4j with provenance

---

### Tool Registry and Execution

The tool registry ([`tools/registry.py`](tools/registry.py)) provides:

1. **Registration**: Tools register with name, description, function, category
2. **Indexing**: Tool descriptions are embedded and stored in ChromaDB
3. **Search**: Semantic search to find relevant tools per query
4. **Execution**: Execute tools with Langfuse tracing

#### Tool Categories:

**Graph Tools** ([`tools/graph_tools.py`](tools/graph_tools.py)):
- `query_entity`: Find entity and neighborhood
- `find_path`: Find shortest path between entities
- `get_neighbors`: Get connected entities
- `get_contradictions`: Find contradicting papers
- `get_supporting`: Find supporting papers

---

## Data Ingestion Pipeline

### Paper Sources

Research Council can ingest papers from multiple sources:

| Source | Description | API Type |
|--------|-------------|----------|
| **PubMed** | Biomedical literature database | BioPython |
| **arXiv** | Preprint server (CS, Physics, Math, etc.) | arXiv.org |
| **Semantic Scholar** | Academic paper search | REST API |
| **Papers With Code** | Papers with associated code | REST API |

#### Ingestion Pipeline:
```
Query PubMed/arXiv/Semantic Scholar
         │
         ▼
    Fetch paper metadata
         │
         ▼
    Parse abstract
         │
         ▼
    Chunk text (500 tokens, 50 overlap)
         │
         ▼
    Embed with MiniLM
         │
         ▼
    Store in ChromaDB
         │
         ▼
    Extract entities (GPT-4o-mini)
         │
         ▼
    Write to Neo4j graph
```

---

### Text Chunking

The chunker ([`ingestion/chunker.py`](ingestion/chunker.py)) splits text with:

- **Chunk size**: 500 tokens (configurable)
- **Overlap**: 50 tokens (to preserve context)
- **Tokenizer**: Simple whitespace tokenizer (fast, CPU-friendly)

---

### Embedding Storage

- **Collection name**: `papers_embeddings`
- **Persistence**: Disk-based (survives restarts)
- **Similarity metric**: Cosine distance
- **Query limits**: Max 10 results per query (performance)

---

## API Endpoints

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/query` | POST | Submit research question to council |
| `/ingest` | POST | Ingest papers from PubMed/arXiv |
| `/graph` | GET | Explore knowledge graph |
| `/search` | POST | Unified search across sources |
| `/upload` | POST | Upload PDF documents |
| `/papers` | GET | List ingested papers |

### Graph Management Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/graph/storages` | GET | List graph storages |
| `/graph/storages` | POST | Create new storage |
| `/graph/storages/{name}` | DELETE | Delete storage |
| `/graph/papers/{id}` | DELETE | Remove paper from graph |

---

## Frontend Interface

The React frontend ([`frontend/src/App.jsx`](frontend/src/App.jsx)) provides:

### Components:

1. **QueryInput**: Text input for research questions
2. **CouncilView**: Displays 4 agent responses with expand/collapse
3. **EvidenceTrail**: Shows citations, key findings, contradictions
4. **GraphViewer**: Interactive D3/Cytoscape.js graph visualization
5. **UnifiedSearch**: Search papers from multiple sources
6. **IngestedPapers**: View/manage ingested papers
7. **PubMedSearch**: Dedicated PubMed search interface

### Features:

- **Session management**: Multiple chat sessions
- **Graph storage selector**: Switch between isolated graphs
- **Confidence visualization**: Color-coded confidence bars
- **Tabbed results**: Answer / Council / Evidence / Graph views
- **Real-time status**: Backend connectivity indicator
- **Token tracking**: Display token usage per query

---

## Configuration and Deployment

### Environment Variables

Create a `.env` file with:

```bash
# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# LLM APIs
GROQ_API_KEY=your_groq_key
OPENROUTER_API_KEY=your_openrouter_key

# Embeddings
EMBEDDING_MODEL=all-MiniLM-L6-v2
CHROMA_PERSIST_DIR=./data/chroma_db
```

### Starting the System

```bash
# 1. Start Neo4j (Docker)
docker run -d --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:5-community

# 2. Install dependencies
uv sync

# 3. Start API
uvicorn api.main:app --reload --port 8000

# 4. Start frontend
cd frontend && npm run dev
```

---

## Hardware and Performance Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| **RAM** | 8 GB | 16 GB |
| **System Memory** | - | For ChromaDB + embeddings |
| **GPU** | Optional | Not needed (CPU embeddings) |
| **Storage** | 10 GB | For Neo4j + ChromaDB |

### Performance Characteristics:

- **Vector embedding**: ~1000 chunks/second on CPU
- **LLM inference**: Groq (fast) + OpenRouter (quality)
- **Graph queries**: <100ms for typical queries
- **Token budget**: ~2000 tokens for context (keeps costs low)

---

## Future Enhancements

### Planned Features:

1. **Community Detection**: Use Louvain algorithm to identify research clusters
2. **Temporal Analysis**: Track how understanding evolves over time
3. **Hypothesis Generation**: Use agents to suggest new research directions
4. **Citation Network Analysis**: Beyond paper-paper citations
5. **Multi-modal Support**: Extract figures, tables from PDFs
6. **Knowledge Graph Caching**: Pre-compute common queries
7. **Custom Agents**: Allow users to define their own agent roles
8. **Batch Processing**: Ingest entire datasets efficiently

---

## Conclusion

Research Council represents a significant advancement in AI-assisted scientific research. By combining:

1. **Graph-based knowledge representation** for rich entity relationships
2. **Hybrid retrieval** for comprehensive context
3. **Multi-agent deliberation** for robust, cross-validated conclusions
4. **Confidence scoring** for calibrated trust
5. **Full provenance** through citations and evidence trails

The system delivers answers that are not just accurate, but also trustworthy, transparent, and actionable for researchers.

---

*Generated: March 2026*
*Version: 0.1.0*
