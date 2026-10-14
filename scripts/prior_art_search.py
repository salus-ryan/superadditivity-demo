#!/usr/bin/env python3
"""Reproducible metadata search for Silo Swarm prior art.

This is a discovery search, not a legal patentability opinion.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

USER_AGENT = "silo-swarm-prior-art/1.0 (mailto:salus-ryan@users.noreply.github.com)"
GENERAL_QUERIES = [
    '"multi-agent debate" evidence aggregation',
    '"mixture of agents" parallel LLM aggregation',
    '"parallel fan-out" typed LLM judgments',
    'probabilistic typed language model decision API',
    '"multi-agent" "incident response" LLM',
    '"AI swarm" incident response dashboard',
    'multi-agent orchestration visualization dashboard',
    'superadditivity multi-agent language model',
    'Shapley contribution multi-agent LLM',
    'LLM "tamper-evident" "audit log"',
    'multi-agent HMAC chained audit log',
    '"agentic AI" "SOC 2" audit logs',
    'cryptographic audit trail AI agents',
    '"evidence silos" connected decision system',
]
ACADEMIC_QUERIES = [
    "multi agent debate evidence aggregation",
    "mixture of agents language models",
    "multi agent language model ensemble aggregation",
    "parallel language model judging",
    "probabilistic LLM as judge",
    "multi agent incident response language model",
    "superadditivity multi agent artificial intelligence",
    "Shapley value large language model agents",
    "tamper evident logging artificial intelligence",
    "cryptographic audit logs autonomous agents",
]
PATENT_QUERIES = [
    '"multi-agent" "audit log"',
    '"language model" "audit trail"',
    '"multi-agent" "incident response"',
    '"AI agent" "tamper-evident"',
    '"parallel" "language model" decision aggregation',
]
GITHUB_QUERIES = [
    'multi agent dashboard llm',
    'llm audit log tamper evident',
    'agent observability audit trail',
    'multi agent incident response',
    'llm hmac audit log',
]


def get(url: str, attempts: int = 3) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    error: Optional[Exception] = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read()
        except Exception as exc:  # preserve failed-source evidence in output
            error = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"request failed after {attempts} attempts: {url}: {error}")


def abstract_from_index(index: Optional[dict[str, list[int]]]) -> Optional[str]:
    if not index:
        return None
    size = max(position for positions in index.values() for position in positions) + 1
    words = [""] * size
    for word, positions in index.items():
        for position in positions:
            words[position] = word
    return " ".join(words)


def search_openalex(query: str) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode({"search": query, "per-page": 20, "select": "id,doi,title,publication_year,cited_by_count,primary_location,abstract_inverted_index,type"})
    payload = json.loads(get(f"https://api.openalex.org/works?{params}"))
    results = []
    for work in payload.get("results", []):
        location = work.get("primary_location") or {}
        source = location.get("source") or {}
        results.append({
            "id": work.get("id"),
            "doi": work.get("doi"),
            "title": work.get("title"),
            "year": work.get("publication_year"),
            "type": work.get("type"),
            "cited_by_count": work.get("cited_by_count"),
            "url": location.get("landing_page_url") or work.get("doi") or work.get("id"),
            "venue": source.get("display_name"),
            "abstract": abstract_from_index(work.get("abstract_inverted_index")),
        })
    return results


def search_bing(query: str) -> list[dict[str, Any]]:
    url = "https://www.bing.com/search?format=rss&q=" + urllib.parse.quote(query)
    root = ET.fromstring(get(url))
    results = []
    for item in root.findall(".//item")[:10]:
        results.append({
            "title": item.findtext("title"),
            "url": item.findtext("link"),
            "snippet": re.sub(r"<[^>]+>", "", item.findtext("description") or ""),
            "published": item.findtext("pubDate"),
        })
    return results


def search_patents(query: str) -> list[dict[str, Any]]:
    inner = "q=" + urllib.parse.quote(query)
    url = "https://patents.google.com/xhr/query?url=" + urllib.parse.quote(inner, safe="") + "&exp="
    payload = json.loads(get(url))
    result_block = payload.get("results", {})
    total = result_block.get("total_num_results")
    records = []
    for cluster in result_block.get("cluster", []):
        for item in cluster.get("result", []):
            patent = item.get("patent") or {}
            number = patent.get("publication_number")
            records.append({
                "publication_number": number,
                "title": html.unescape(re.sub(r"<[^>]+>", "", patent.get("title") or "")).strip(),
                "url": f"https://patents.google.com/patent/{number}/en" if number else None,
                "snippet": html.unescape(re.sub(r"<[^>]+>", "", patent.get("snippet") or "")).strip(),
                "priority_date": patent.get("priority_date"),
                "filing_date": patent.get("filing_date"),
                "publication_date": patent.get("publication_date"),
                "inventor": patent.get("inventor"),
                "assignee": patent.get("assignee"),
                "query_total_results": total,
            })
    return records[:10]


def search_github(query: str) -> list[dict[str, Any]]:
    command = ["gh", "api", "--method", "GET", "search/repositories", "-f", f"q={query}", "-f", "per_page=10"]
    payload = json.loads(subprocess.check_output(command, text=True))
    return [{
        "name": item["full_name"],
        "url": item["html_url"],
        "description": item.get("description"),
        "stars": item.get("stargazers_count"),
        "updated_at": item.get("updated_at"),
        "license": (item.get("license") or {}).get("spdx_id"),
    } for item in payload.get("items", [])]


def collect() -> dict[str, Any]:
    output: dict[str, Any] = {
        "schema_version": "1.0",
        "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "scope_note": "Discovery metadata for technical novelty review; not a legal opinion.",
        "sources": {},
        "errors": [],
    }
    for source, queries, search in [
        ("openalex", ACADEMIC_QUERIES, search_openalex),
        ("bing", GENERAL_QUERIES, search_bing),
        ("google_patents", PATENT_QUERIES, search_patents),
        ("github", GITHUB_QUERIES, search_github),
    ]:
        batches = []
        for query in queries:
            try:
                batches.append({"query": query, "results": search(query)})
            except Exception as exc:
                output["errors"].append({"source": source, "query": query, "error_type": type(exc).__name__, "error": str(exc)[:300]})
                batches.append({"query": query, "results": []})
            time.sleep(0.35)
        output["sources"][source] = batches
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("research/prior_art_results.json"))
    args = parser.parse_args()
    payload = collect()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    counts = {source: sum(len(batch["results"]) for batch in batches) for source, batches in payload["sources"].items()}
    print(json.dumps({"output": str(args.output), "counts": counts, "errors": len(payload["errors"])}, indent=2))


if __name__ == "__main__":
    main()
