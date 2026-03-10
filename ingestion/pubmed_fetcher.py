"""
PubMed fetcher — search & download paper metadata via NCBI Entrez.

Uses Biopython's Entrez module. Requires ENTREZ_EMAIL in .env.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from Bio import Entrez
from tenacity import retry, stop_after_attempt, wait_exponential

from config import ENTREZ_EMAIL

logger = logging.getLogger(__name__)

Entrez.email = ENTREZ_EMAIL


@dataclass
class PaperMetadata:
    """Minimal representation of a PubMed article."""

    pmid: str
    title: str
    abstract: str
    authors: list[str] = field(default_factory=list)
    journal: str = ""
    year: Optional[int] = None
    doi: Optional[str] = None


# ── Public API ────────────────────────────────────────────────────────────────


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def search_pubmed(query: str, max_results: int = 20) -> list[str]:
    """Return a list of PubMed IDs matching *query*."""
    handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results, sort="relevance")
    record = Entrez.read(handle)
    handle.close()
    pmids: list[str] = record.get("IdList", [])
    logger.info("PubMed search '%s' → %d results", query, len(pmids))
    return pmids


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def fetch_details(pmids: list[str]) -> list[PaperMetadata]:
    """Fetch title, abstract, authors, etc. for a batch of PubMed IDs."""
    if not pmids:
        return []

    handle = Entrez.efetch(db="pubmed", id=",".join(pmids), rettype="xml")
    records = Entrez.read(handle)
    handle.close()

    papers: list[PaperMetadata] = []
    for article in records.get("PubmedArticle", []):
        medline = article["MedlineCitation"]
        art = medline["Article"]

        # Title
        title = str(art.get("ArticleTitle", ""))

        # Abstract — may be structured (multiple sections)
        abstract_parts = art.get("Abstract", {}).get("AbstractText", [])
        abstract = " ".join(str(p) for p in abstract_parts)

        # Authors
        author_list = art.get("AuthorList", [])
        authors = []
        for a in author_list:
            last = a.get("LastName", "")
            first = a.get("ForeName", "")
            if last:
                authors.append(f"{last}, {first}".strip(", "))

        # Journal & Year
        journal_info = art.get("Journal", {})
        journal = str(journal_info.get("Title", ""))
        pub_date = journal_info.get("JournalIssue", {}).get("PubDate", {})
        year_str = pub_date.get("Year", "")
        year = int(year_str) if year_str.isdigit() else None

        # DOI
        doi = None
        for eid in article.get("PubmedData", {}).get("ArticleIdList", []):
            if eid.attributes.get("IdType") == "doi":
                doi = str(eid)

        papers.append(
            PaperMetadata(
                pmid=str(medline["PMID"]),
                title=title,
                abstract=abstract,
                authors=authors,
                journal=journal,
                year=year,
                doi=doi,
            )
        )

    logger.info("Fetched details for %d papers", len(papers))
    return papers


def search_and_fetch(query: str, max_results: int = 20) -> list[PaperMetadata]:
    """Convenience: search PubMed and return full metadata in one call."""
    pmids = search_pubmed(query, max_results=max_results)
    return fetch_details(pmids)
