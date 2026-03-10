"""
Quick smoke test — verifies every layer of the Research Council stack.

Run:  python smoke_test.py
"""

import asyncio
import os
import sys

from rich.console import Console
from rich.table import Table

console = Console()


def header(msg: str):
    console.print(f"\n[bold cyan]{'═' * 60}[/]")
    console.print(f"[bold cyan]  {msg}[/]")
    console.print(f"[bold cyan]{'═' * 60}[/]")


async def main():
    results: list[tuple[str, bool, str]] = []

    # ── 1. Config ─────────────────────────────────────────
    header("1/7  Config & Environment")
    try:
        from config import (
            CHROMA_PERSIST_DIR,
            EMBEDDING_MODEL,
            GROQ_API_KEY,
            NEO4J_URI,
            OPENROUTER_API_KEY,
        )

        has_groq = bool(GROQ_API_KEY and not GROQ_API_KEY.startswith("gsk_..."))
        has_or = bool(OPENROUTER_API_KEY and not OPENROUTER_API_KEY.startswith("sk-or-v1-..."))
        console.print(f"  GROQ_API_KEY:       {'[green]set[/]' if has_groq else '[red]missing[/]'}")
        console.print(f"  OPENROUTER_API_KEY: {'[green]set[/]' if has_or else '[red]missing[/]'}")
        console.print(f"  NEO4J_URI:          {NEO4J_URI}")
        console.print(f"  EMBEDDING_MODEL:    {EMBEDDING_MODEL}")
        results.append(("Config loaded", True, ""))
    except Exception as e:
        results.append(("Config loaded", False, str(e)))
        console.print(f"  [red]FAIL: {e}[/]")

    # ── 2. Neo4j ──────────────────────────────────────────
    header("2/7  Neo4j Connection")
    try:
        from graph.schema import get_driver

        driver = get_driver()
        with driver.session() as s:
            r = s.run("SHOW CONSTRAINTS")
            constraints = [rec["name"] for rec in r]
            r2 = s.run("MATCH (n) RETURN count(n) AS cnt")
            node_count = r2.single()["cnt"]
        driver.close()
        console.print(f"  Constraints: {len(constraints)}")
        console.print(f"  Total nodes: {node_count}")
        results.append(("Neo4j connected", True, f"{len(constraints)} constraints, {node_count} nodes"))
    except Exception as e:
        results.append(("Neo4j connected", False, str(e)))
        console.print(f"  [red]FAIL: {e}[/]")

    # ── 3. Embeddings (CPU) ───────────────────────────────
    header("3/7  Embedding Model (CPU)")
    try:
        from ingestion.embedding_pipeline import embed_texts

        vecs = embed_texts(["test sentence for embeddings"])
        dim = len(vecs[0])
        console.print(f"  Output dimension: {dim}")
        console.print(f"  Vector sample:    [{vecs[0][0]:.4f}, {vecs[0][1]:.4f}, …]")
        results.append(("Embeddings (CPU)", True, f"dim={dim}"))
    except Exception as e:
        results.append(("Embeddings (CPU)", False, str(e)))
        console.print(f"  [red]FAIL: {e}[/]")

    # ── 4. ChromaDB ───────────────────────────────────────
    header("4/7  ChromaDB Vector Store")
    try:
        from ingestion.embedding_pipeline import get_or_create_collection

        coll = get_or_create_collection("smoke_test")
        coll.upsert(ids=["test1"], documents=["hello world"], embeddings=[vecs[0]])
        res = coll.query(query_embeddings=[vecs[0]], n_results=1)
        console.print(f"  Collection:   smoke_test")
        console.print(f"  Query result: {res['documents'][0][0][:50]}")
        # Cleanup
        from ingestion.embedding_pipeline import get_chroma_client
        get_chroma_client().delete_collection("smoke_test")
        results.append(("ChromaDB", True, "read/write OK"))
    except Exception as e:
        results.append(("ChromaDB", False, str(e)))
        console.print(f"  [red]FAIL: {e}[/]")

    # ── 5. Groq API ───────────────────────────────────────
    header("5/7  Groq API")
    try:
        from council.agents import call_groq

        text, tokens = await call_groq(
            model="llama-3.3-70b-versatile",
            system_prompt="You are a test assistant.",
            user_message="Reply with exactly: GROQ_OK",
            max_tokens=20,
        )
        console.print(f"  Response: {text.strip()[:60]}")
        console.print(f"  Tokens:   {tokens}")
        results.append(("Groq API", True, f"{tokens} tokens"))
    except Exception as e:
        results.append(("Groq API", False, str(e)))
        console.print(f"  [red]FAIL: {e}[/]")

    # ── 6. OpenRouter API ─────────────────────────────────
    header("6/7  OpenRouter API")
    try:
        from council.agents import call_openrouter

        text, tokens = await call_openrouter(
            model="openai/gpt-4o-mini",
            system_prompt="You are a test assistant.",
            user_message="Reply with exactly: OPENROUTER_OK",
            max_tokens=20,
        )
        console.print(f"  Response: {text.strip()[:60]}")
        console.print(f"  Tokens:   {tokens}")
        results.append(("OpenRouter API", True, f"{tokens} tokens"))
    except Exception as e:
        results.append(("OpenRouter API", False, str(e)))
        console.print(f"  [red]FAIL: {e}[/]")

    # ── 7. Tool Registry ──────────────────────────────────
    header("7/7  Tool Registry & Search")
    try:
        from orchestrator.bigtool_agent import ensure_tools_indexed, select_tools

        ensure_tools_indexed()
        tools = select_tools("find contradictions in BRCA1 research")
        names = [t["name"] for t in tools]
        console.print(f"  Tools found: {names}")
        results.append(("Tool Registry", True, f"{len(names)} tools selected"))
    except Exception as e:
        results.append(("Tool Registry", False, str(e)))
        console.print(f"  [red]FAIL: {e}[/]")

    # ── Summary ───────────────────────────────────────────
    header("RESULTS SUMMARY")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Component", style="cyan")
    table.add_column("Status")
    table.add_column("Details", style="dim")

    passed = 0
    for name, ok, detail in results:
        status = "[green]✅ PASS[/]" if ok else "[red]❌ FAIL[/]"
        table.add_row(name, status, detail)
        if ok:
            passed += 1

    console.print(table)
    console.print(f"\n[bold]  {passed}/{len(results)} checks passed[/]\n")

    if passed == len(results):
        console.print("[bold green]  🎉 All systems operational — ready to ingest papers![/]\n")
    else:
        console.print("[bold yellow]  ⚠️  Fix failing checks above before proceeding.[/]\n")


if __name__ == "__main__":
    asyncio.run(main())
