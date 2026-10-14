#!/usr/bin/env python3
"""Claim-oriented patent discovery and reproducible keyword claim charts.

This tool assists technical prior-art review. It does not provide legal advice,
claim construction, a patentability opinion, or freedom-to-operate clearance.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

USER_AGENT = "silo-swarm-patent-landscape/1.0 (research; contact: salus-ryan@users.noreply.github.com)"
GOOGLE_XHR = "https://patents.google.com/xhr/query"
GOOGLE_PATENT = "https://patents.google.com/patent/{number}/en"
USPTO_PDF = "https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/{number}"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def clean_markup(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value or ""))).strip()


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


class CachedClient:
    def __init__(self, cache_dir: Path, delay_seconds: float = 3.0):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.delay_seconds = delay_seconds
        self.last_request = 0.0

    def get(self, url: str) -> bytes:
        cache_path = self.cache_dir / (hashlib.sha256(url.encode()).hexdigest() + ".bin")
        if cache_path.exists():
            return cache_path.read_bytes()
        error: Optional[Exception] = None
        for wait in (0, 5, 15):
            if wait:
                time.sleep(wait)
            elapsed = time.monotonic() - self.last_request
            if elapsed < self.delay_seconds:
                time.sleep(self.delay_seconds - elapsed)
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
            try:
                self.last_request = time.monotonic()
                with urllib.request.urlopen(request, timeout=60) as response:
                    data = response.read()
                cache_path.write_bytes(data)
                return data
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
                error = exc
        raise RuntimeError(f"request failed: {url}: {error}")


def google_query_url(query: str, page: int, cutoff: str) -> str:
    inner = urllib.parse.urlencode({
        "q": query,
        "before": "priority:" + cutoff.replace("-", ""),
        "language": "ENGLISH",
        "page": page,
    })
    return GOOGLE_XHR + "?" + urllib.parse.urlencode({"url": inner, "exp": ""})


def search_google_patents(client: CachedClient, query: str, cutoff: str, pages: int) -> Tuple[int, List[Dict[str, Any]]]:
    records: List[Dict[str, Any]] = []
    total = 0
    for page in range(pages):
        payload = json.loads(client.get(google_query_url(query, page, cutoff)))
        block = payload.get("results", {})
        total = int(block.get("total_num_results") or total or 0)
        for cluster in block.get("cluster", []):
            for item in cluster.get("result", []):
                patent = item.get("patent") or {}
                number = patent.get("publication_number")
                records.append({
                    "publication_number": number,
                    "title": clean_markup(patent.get("title") or ""),
                    "snippet": clean_markup(patent.get("snippet") or ""),
                    "priority_date": patent.get("priority_date"),
                    "filing_date": patent.get("filing_date"),
                    "publication_date": patent.get("publication_date"),
                    "inventor": patent.get("inventor"),
                    "assignee": patent.get("assignee"),
                    "url": GOOGLE_PATENT.format(number=number) if number else None,
                    "source_query": query,
                    "search_rank": item.get("rank"),
                })
    return total, records


def parse_meta_tags(page: str) -> List[Dict[str, str]]:
    tags = []
    for tag in re.findall(r"<meta\s+[^>]*>", page, re.I):
        attrs = {}
        for key, _quote, value in re.findall(r"([:\w.-]+)\s*=\s*([\"'])(.*?)\2", tag, re.I | re.S):
            attrs[key.lower()] = html.unescape(value)
        tags.append(attrs)
    return tags


def meta_values(tags: List[Dict[str, str]], name: str, scheme: Optional[str] = None) -> List[str]:
    values = []
    for tag in tags:
        if tag.get("name", "").lower() != name.lower():
            continue
        if scheme is not None and tag.get("scheme", "").lower() != scheme.lower():
            continue
        if tag.get("content"):
            values.append(clean_markup(tag["content"]))
    return values


def fetch_uspto_pdf_detail(client: CachedClient, number: str) -> Dict[str, Any]:
    match = re.match(r"^US(\d+)[A-Z]\d?$", number)
    if not match:
        raise ValueError("USPTO PDF fallback supports US publications only")
    pdf = client.get(USPTO_PDF.format(number=match.group(1)))
    if not pdf.startswith(b"%PDF"):
        raise ValueError("USPTO response was not a PDF")
    converted = subprocess.run(
        ["pdftotext", "-layout", "-", "-"], input=pdf, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=True,
    ).stdout.decode("utf-8", "ignore")
    claim_match = re.search(r"(?:what is claimed is:|claims)\s*([\s\S]+?)(?:\n\s*abstract\s*\n|\Z)", converted, re.I)
    claim_block = claim_match.group(1) if claim_match else ""
    claims = [clean_markup(part) for part in re.split(r"(?m)^\s*(?=\d+\.\s)", claim_block) if re.match(r"^\d+\.\s", part.strip())]
    abstract_match = re.search(r"\n\s*abstract\s*\n([\s\S]{20,2500}?)(?:\n\s*(?:drawings|background|field|what is claimed is:)\s*\n|\Z)", converted, re.I)
    return {
        "publication_number": number,
        "title": "",
        "abstract": clean_markup(abstract_match.group(1)) if abstract_match else "",
        "claims": claims,
        "cpc": [],
        "relations": [],
        "cited_publications": [],
        "detail_url": USPTO_PDF.format(number=match.group(1)),
        "detail_source": "USPTO published-document PDF",
        "detail_sha256": hashlib.sha256(pdf).hexdigest(),
        "pdf_text_sha256": hashlib.sha256(converted.encode("utf-8")).hexdigest(),
    }


def fetch_patent_detail(client: CachedClient, number: str) -> Dict[str, Any]:
    page = client.get(GOOGLE_PATENT.format(number=number)).decode("utf-8", "ignore")
    tags = parse_meta_tags(page)
    claims = [clean_markup(match) for match in re.findall(r'<div[^>]+class="[^"]*claim-text[^"]*"[^>]*>([\s\S]*?)</div>', page, re.I)]
    abstracts = meta_values(tags, "DC.description")
    titles = meta_values(tags, "DC.title")
    cpc = meta_values(tags, "DC.subject", "CPC")
    relations = meta_values(tags, "DC.relation")
    cited_numbers = sorted(set(re.findall(r'itemprop="publicationNumber"[^>]*>\s*([^<\s]+)', page, re.I)))
    return {
        "publication_number": number,
        "title": titles[0] if titles else "",
        "abstract": abstracts[0] if abstracts else "",
        "claims": claims,
        "cpc": cpc,
        "relations": relations,
        "cited_publications": cited_numbers,
        "detail_url": GOOGLE_PATENT.format(number=number),
        "detail_sha256": hashlib.sha256(page.encode("utf-8")).hexdigest(),
    }


def sentences(value: str) -> Iterable[str]:
    for sentence in re.split(r"(?<=[.;])\s+|\n+", clean_markup(value)):
        if sentence:
            yield sentence


def match_element(element: Dict[str, Any], fields: List[Tuple[str, str, int]]) -> Dict[str, Any]:
    evidence = []
    score = 0
    matched_terms = set()
    for field_name, value, weight in fields:
        normalized = normalize(value)
        for term in element["terms"]:
            if normalize(term) in normalized:
                matched_terms.add(term)
                score = max(score, weight)
                excerpt = next((s for s in sentences(value) if normalize(term) in normalize(s)), value[:500])
                evidence.append({"field": field_name, "term": term, "excerpt": excerpt[:700]})
                break
    return {
        "id": element["id"],
        "name": element["name"],
        "matched": bool(evidence),
        "weight": score,
        "matched_terms": sorted(matched_terms),
        "evidence": evidence[:3],
    }


def score_record(record: Dict[str, Any], elements: List[Dict[str, Any]]) -> Dict[str, Any]:
    detail = record.get("detail") or {}
    fields = [
        ("title", detail.get("title") or record.get("title") or "", 2),
        ("snippet", record.get("snippet") or "", 1),
        ("abstract", detail.get("abstract") or "", 3),
        ("claims", " ".join(detail.get("claims") or []), 5),
    ]
    chart = [match_element(element, fields) for element in elements]
    coverage = sum(1 for row in chart if row["matched"])
    weighted_score = sum(row["weight"] for row in chart)
    claim_coverage = sum(1 for row in chart if any(e["field"] == "claims" for e in row["evidence"]))
    output = dict(record)
    output["element_chart"] = chart
    output["element_coverage"] = coverage
    output["claim_element_coverage"] = claim_coverage
    output["weighted_score"] = weighted_score
    return output


def family_proxy(record: Dict[str, Any]) -> str:
    title = normalize(record.get("title") or (record.get("detail") or {}).get("title") or "")
    title = " ".join(title.split()[:18])
    return f"{record.get('priority_date') or 'unknown'}::{title}"


def import_seed_results(path: Optional[Path]) -> List[Dict[str, Any]]:
    if not path or not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    source = payload.get("sources", {}).get("google_patents", [])
    return [dict(record, source_query=batch.get("query"), imported_seed=True) for batch in source for record in batch.get("results", [])]


def render_report(payload: Dict[str, Any], path: Path) -> None:
    lines = [
        "# Silo Swarm claim-oriented patent landscape",
        "",
        f"Generated: {payload['generated_at']}",
        "",
        "> Discovery aid only. This is not legal advice, claim construction, a patentability opinion, or freedom-to-operate clearance.",
        "",
        "## Coverage",
        "",
        f"- New queries attempted in this run: {payload['stats']['queries_attempted']}",
        f"- Imported Google Patents query batches: {payload['stats']['seed_query_batches']}",
        f"- Search hits reported by Google Patents across new queries: {payload['stats']['reported_hits_sum']}",
        f"- Retrieved result rows: {payload['stats']['retrieved_rows']}",
        f"- Unique publications: {payload['stats']['unique_publications']}",
        f"- Proxy families: {payload['stats']['proxy_families']}",
        f"- Full patent documents retrieved: {payload['stats']['details_retrieved']}",
        f"- Documents with machine-extracted claims: {payload['stats']['details_with_claims']}",
        f"- Machine-extracted claims: {payload['stats']['claims_extracted']}",
        f"- Request failures: {len(payload['errors'])}",
        "",
    ]
    if payload["stats"]["details_retrieved"] and not payload["stats"]["claims_extracted"]:
        lines += [
            "> **Claim-text gap:** the retrieved USPTO PDFs were image-only. They are cryptographically cached, but claim coverage remains unscored until OCR or a text source is available.",
            "",
        ]
    lines += [
        "## Highest-overlap publications",
        "",
        "| Coverage | Claim coverage | Score | Publication | Priority | Title |",
        "|---:|---:|---:|---|---|---|",
    ]
    for record in payload["ranked"][:25]:
        lines.append("| {}/7 | {}/7 | {} | [{}]({}) | {} | {} |".format(
            record["element_coverage"], record["claim_element_coverage"], record["weighted_score"],
            record.get("publication_number") or "unknown", record.get("url") or "", record.get("priority_date") or "—",
            (record.get("title") or "").replace("|", "\\|"),
        ))
    lines += ["", "## Preliminary element charts", ""]
    for record in payload["ranked"][:10]:
        lines += [
            f"### {record.get('publication_number')}: {record.get('title')}",
            "",
            f"Priority: {record.get('priority_date') or 'unknown'} · Assignee: {record.get('assignee') or 'unknown'} · [source]({record.get('url') or ''})",
            "",
        ]
        for row in record["element_chart"]:
            mark = "✓" if row["matched"] else "—"
            lines.append(f"- **{mark} {row['id']} — {row['name']}**")
            if row["evidence"]:
                evidence = row["evidence"][0]
                lines.append(f"  - `{evidence['field']}` / term `{evidence['term']}`: “{evidence['excerpt']}”")
        lines.append("")
    lines += [
        "## Interpretation limits",
        "",
        "Keyword coverage is a retrieval signal, not legal anticipation. A single earlier reference generally must disclose every properly construed limitation for novelty; obviousness may rely on combinations and motivation to combine. Abstracts and snippets cannot replace independent-claim review. Proxy-family grouping by title and priority date is not a substitute for INPADOC family analysis. Legal status shown by public databases may be incomplete or delayed. Unpublished applications create an unavoidable blind spot.",
        "",
        "## Next human review queue",
        "",
        "1. Read every independent claim for the top 25 and correct false-positive element mappings.",
        "2. Expand CPC/IPC classes from the strongest seeds and rerun classification searches.",
        "3. Chase backward/forward citations and family members for every high-coverage seed.",
        "4. Build separate anticipation and obviousness charts with a fixed claim construction.",
        "5. Separate patentability from freedom-to-operate and review live claims by jurisdiction.",
        "6. Have qualified patent counsel validate any filing, clearance, or public novelty claim.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("research/patent_search_config.json"))
    parser.add_argument("--seed-results", type=Path, default=Path("research/prior_art_results.json"))
    parser.add_argument("--output", type=Path, default=Path("research/patent_landscape.json"))
    parser.add_argument("--report", type=Path, default=Path("research/PATENT_LANDSCAPE.md"))
    parser.add_argument("--cache", type=Path, default=Path("research/.patent-cache"))
    parser.add_argument("--pages", type=int, default=1)
    parser.add_argument("--detail-limit", type=int, default=25)
    parser.add_argument("--delay", type=float, default=3.0)
    parser.add_argument("--offline", action="store_true", help="Use existing seed results only; make no network requests")
    parser.add_argument("--skip-search", action="store_true", help="Skip new queries but retrieve full details for seeded publications")
    parser.add_argument("--max-consecutive-failures", type=int, default=3, help="Open the network circuit after repeated source failures")
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    client = CachedClient(args.cache, args.delay)
    errors: List[Dict[str, Any]] = []
    all_records = import_seed_results(args.seed_results)
    seed_query_batches = 0
    if args.seed_results and args.seed_results.exists():
        seed_payload = json.loads(args.seed_results.read_text(encoding="utf-8"))
        seed_query_batches = len(seed_payload.get("sources", {}).get("google_patents", []))
    query_runs = []
    reported_hits_sum = 0

    network_available = not args.offline
    consecutive_failures = 0
    if network_available and not args.skip_search:
        for query in config["queries"]:
            if consecutive_failures >= args.max_consecutive_failures:
                network_available = False
                errors.append({"stage": "search", "query": "remaining queries", "error_type": "CircuitOpen", "error": "source disabled after repeated failures; seed results preserved"})
                break
            try:
                total, records = search_google_patents(client, query, config["cutoff_priority_date"], args.pages)
                reported_hits_sum += total
                all_records.extend(records)
                query_runs.append({"query": query, "reported_hits": total, "retrieved": len(records)})
                consecutive_failures = 0
            except Exception as exc:
                consecutive_failures += 1
                errors.append({"stage": "search", "query": query, "error_type": type(exc).__name__, "error": str(exc)[:500]})
                query_runs.append({"query": query, "reported_hits": None, "retrieved": 0})

    by_number: Dict[str, Dict[str, Any]] = {}
    for record in all_records:
        number = record.get("publication_number")
        if number and number not in by_number:
            by_number[number] = record

    preliminary = [score_record(record, config["claim_elements"]) for record in by_number.values()]
    preliminary.sort(key=lambda row: (row["element_coverage"], row["weighted_score"]), reverse=True)
    detail_numbers = []
    for number in config.get("seed_publications", []):
        if number not in detail_numbers:
            detail_numbers.append(number)
    for record in preliminary:
        number = record.get("publication_number")
        if number and number not in detail_numbers:
            detail_numbers.append(number)
        if len(detail_numbers) >= args.detail_limit:
            break

    details_retrieved = 0
    if not args.offline:
        for number in detail_numbers[:args.detail_limit]:
            try:
                if number.startswith("US"):
                    try:
                        detail = fetch_uspto_pdf_detail(client, number)
                    except (ValueError, RuntimeError, subprocess.SubprocessError):
                        if not network_available:
                            raise RuntimeError("USPTO detail failed and Google Patents circuit is open")
                        detail = fetch_patent_detail(client, number)
                elif network_available:
                    detail = fetch_patent_detail(client, number)
                else:
                    raise RuntimeError("Google Patents circuit is open for non-US detail")
                details_retrieved += 1
                if number not in by_number:
                    by_number[number] = {"publication_number": number, "url": GOOGLE_PATENT.format(number=number)}
                by_number[number]["detail"] = detail
                if detail.get("title") and not by_number[number].get("title"):
                    by_number[number]["title"] = detail["title"]
            except Exception as exc:
                errors.append({"stage": "detail", "publication_number": number, "error_type": type(exc).__name__, "error": str(exc)[:500]})

    ranked = [score_record(record, config["claim_elements"]) for record in by_number.values()]
    ranked.sort(key=lambda row: (row["claim_element_coverage"], row["element_coverage"], row["weighted_score"]), reverse=True)
    families = {family_proxy(record) for record in ranked}
    claims_extracted = sum(len((record.get("detail") or {}).get("claims") or []) for record in ranked)
    details_with_claims = sum(1 for record in ranked if (record.get("detail") or {}).get("claims"))
    payload = {
        "schema_version": "1.0",
        "generated_at": utc_now(),
        "disclaimer": "Discovery aid only; not legal advice, patentability, or freedom-to-operate clearance.",
        "config": config,
        "query_runs": query_runs,
        "errors": errors,
        "stats": {
            "queries_attempted": len(query_runs),
            "seed_query_batches": seed_query_batches,
            "reported_hits_sum": reported_hits_sum,
            "retrieved_rows": len(all_records),
            "unique_publications": len(by_number),
            "proxy_families": len(families),
            "details_retrieved": details_retrieved,
            "details_with_claims": details_with_claims,
            "claims_extracted": claims_extracted,
        },
        "ranked": ranked,
    }
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    render_report(payload, args.report)
    print(json.dumps({"output": str(args.output), "report": str(args.report), "stats": payload["stats"], "errors": len(errors)}, indent=2))


if __name__ == "__main__":
    main()
