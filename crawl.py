#!/usr/bin/env python3
"""A bounded, cached CCCG literature crawl. Keyword hits are leads, not proofs."""
import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser

ROOT = Path(__file__).resolve().parent
BASE = "https://cccg.ca/"
AGENT = "CCCGOptimizationSurvey/1.0"
TERMS = {
    "second-order-cone": r"second[ -]order con(?:e|ic)|\bSOCP\b",
    "semidefinite-programming": r"semi[ -]?definite program",
    "convex-optimization": r"convex (?:optimi[sz]ation|program)",
    "linear-programming": r"\blinear program(?:ming|s)?|\bLP-type\b",
    "quadratic-programming": r"quadratic program",
    "interior-point": r"interior[ -]point\s+(?:method|algorithm|solver|approach)",
    "minimum-cost-flow": r"min(?:imum)?[ -]cost[ -]flow",
    "parametric-search": r"parametric search",
}


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def clean(text):
    return " ".join(text.split())


def canonical(url):
    p = urlparse(url)
    if p.hostname not in {"cccg.ca", "www.cccg.ca"}:
        raise ValueError(f"Outside the CCCG archive: {url}")
    if p.scheme not in {"http", "https"}:
        raise ValueError(f"Unsupported scheme: {url}")
    return urlunparse(("https", "cccg.ca", p.path, "", p.query, ""))


class IndexParser(HTMLParser):
    """Read paper metadata from the archive's bibliographic HTML indexes."""
    def __init__(self, base):
        super().__init__(convert_charrefs=True)
        self.base, self.lines, self.papers, self.links = base, [""], {}, []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "dt":
            self.lines = [""]
        elif tag == "dd":
            self.lines = [""]
        elif tag == "br":
            self.lines.append("")
        elif tag == "a" and "href" in attrs:
            try:
                url = canonical(urljoin(self.base, attrs["href"]))
            except ValueError:
                return
            self.links.append(url)
            if urlparse(url).path.lower().endswith(".pdf"):
                parts = [clean(x) for x in self.lines if clean(x)]
                self.papers.setdefault(url, {
                    "url": url,
                    "authors": parts[0] if len(parts) >= 3 else "",
                    "title": parts[1] if len(parts) >= 3 else Path(urlparse(url).path).name,
                    "source_type": "paper",
                })

    def handle_data(self, data):
        self.lines[-1] += data


def classify(text):
    normalized = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    # References can mention a solver the paper never uses.
    body = re.split(r"(?im)^\s*(?:\d+[. ]+)?References\s*$", normalized, maxsplit=1)[0]
    body = clean(body)
    hits = [name for name, pattern in TERMS.items() if re.search(pattern, body, re.I)]
    return sorted(hits)


def group_papers(records):
    groups = {}
    for r in records:
        key = (r["year"], r["title"], r["authors"])
        group = groups.setdefault(key, {"year": r["year"], "title": r["title"],
            "authors": r["authors"], "source_type": r["source_type"],
            "urls": [], "optimization_terms": [], "status": "no_keyword_hit"})
        group["urls"].append(r["url"])
        group["optimization_terms"] = sorted(set(group["optimization_terms"] + r["optimization_terms"]))
        if group["optimization_terms"]:
            group["status"] = "candidate_unreviewed"
        elif r["error"]:
            group["status"] = "incomplete_extraction"
    return list(groups.values())


class Fetcher:
    def __init__(self, cache, delay):
        self.cache, self.delay, self.last = cache, delay, 0.0
        self.cache.mkdir(parents=True, exist_ok=True)
        self.requests, self.cache_hits = 0, 0
        self.robot = None
        self.robot_status = None

    def get(self, url, check_robots=True):
        url = canonical(url)
        if check_robots and self.robot and not self.robot.can_fetch(AGENT, url):
            raise RuntimeError(f"robots.txt disallows {url}")
        key = hashlib.sha256(url.encode()).hexdigest()
        dest = self.cache / key
        meta_path = self.cache / (key + ".json")
        if dest.exists() and meta_path.exists():
            self.cache_hits += 1
            return dest, json.loads(meta_path.read_text())
        time.sleep(max(0.0, self.delay - (time.monotonic() - self.last)))
        part = self.cache / (key + ".part")
        result = subprocess.run([
            "curl", "--silent", "--show-error", "--location",
            "--proto", "=https", "--proto-redir", "=https",
            "--max-time", "45", "--user-agent", AGENT,
            "--output", str(part), "--write-out", "%{http_code}", url,
        ], capture_output=True, text=True)
        self.last = time.monotonic()
        self.requests += 1
        status = int(result.stdout) if result.stdout.isdigit() else 0
        if result.returncode or status != 200:
            part.unlink(missing_ok=True)
            raise RuntimeError(f"HTTP {status}; curl {result.returncode}: {result.stderr.strip()}")
        part.replace(dest)
        metadata = {"url": url, "fetched_at": utcnow(), "http_status": status,
                    "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
                    "bytes": dest.stat().st_size}
        meta_path.write_text(json.dumps(metadata, indent=2) + "\n")
        return dest, metadata

    def load_robots(self):
        try:
            path, meta = self.get(BASE + "robots.txt", check_robots=False)
        except RuntimeError as exc:
            if "HTTP 404;" not in str(exc):
                raise RuntimeError(f"Cannot establish archive crawl rules: {exc}") from exc
            self.robot_status = "HTTP 404: no robots.txt rules supplied"
            return
        self.robot = RobotFileParser()
        self.robot.parse(path.read_text(errors="replace").splitlines())
        self.robot_status = {"url": meta["url"], "sha256": meta["sha256"]}
        self.delay = max(self.delay, self.robot.crawl_delay(AGENT) or 0)


def extract(path):
    txt = path.with_suffix(".txt")
    if not txt.exists():
        result = subprocess.run(["pdftotext", "-layout", str(path), str(txt)],
                                capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError("PDF extraction failed: " + result.stderr.strip())
    text = txt.read_text(errors="replace")
    if len(clean(text)) < 40:
        raise RuntimeError("No usable text layer; OCR/manual reading needed")
    return text


def run(args):
    started = utcnow()
    fetch = Fetcher(args.cache, args.delay)
    fetch.load_robots()
    home, _ = fetch.get(BASE)
    root = IndexParser(BASE)
    root.feed(home.read_text(errors="replace"))
    papers, indexes, errors = {}, [], []
    for year in args.years:
        prefix = f"{BASE}proceedings/{year}/"
        year_links = sorted(set(u for u in root.links if u.startswith(prefix)))
        if not year_links:
            errors.append({"year": year, "error": "No same-host year link on the archive homepage"})
        for index_url in year_links:
            try:
                path, meta = fetch.get(index_url)
                indexes.append(meta)
                if path.read_bytes()[:5] == b"%PDF-":
                    papers[index_url] = {"url": index_url, "year": year,
                                         "title": f"CCCG {year} proceedings volume", "authors": "",
                                         "source_type": "proceedings_volume"}
                else:
                    parser = IndexParser(index_url)
                    parser.feed(path.read_text(errors="replace"))
                    for url, record in parser.papers.items():
                        if url.startswith(prefix):
                            papers[url] = dict(record, year=year)
            except (RuntimeError, OSError) as exc:
                errors.append({"url": index_url, "error": str(exc)})
    discovered = len(papers)
    selected = sorted(papers.values(), key=lambda r: (r["year"], r["url"]))
    if args.max_documents:
        selected = selected[:args.max_documents]
    records = []
    for i, record in enumerate(selected, 1):
        try:
            path, meta = fetch.get(record["url"])
            text = extract(path)
            hits = classify(text)
            record.update({"fetch": meta, "characters": len(text), "optimization_terms": hits,
                           "status": "candidate_unreviewed" if hits else "no_keyword_hit",
                           "error": None})
        except (RuntimeError, OSError) as exc:
            record.update({"status": "fetch_or_extraction_failed", "error": str(exc),
                           "optimization_terms": []})
        records.append(record)
        print(f"[{i}/{len(selected)}] {record['status']}: {record['title']}", flush=True)
    finished = utcnow()
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    groups = group_papers(records)
    report = {"started_at": started, "completed_at": finished, "years": args.years,
              "source": BASE, "robots": fetch.robot_status, "delay_seconds": fetch.delay,
              "documents_discovered": discovered, "documents_attempted": len(records),
              "documents_extracted": sum(r["error"] is None for r in records),
              "candidate_documents": sum(r["status"] == "candidate_unreviewed" for r in records),
              "bibliographic_groups": len(groups),
              "candidate_groups": sum(g["status"] == "candidate_unreviewed" for g in groups),
              "network_requests": fetch.requests, "cache_hits": fetch.cache_hits,
              "truncated": len(selected) < discovered, "index_errors": errors,
              "scope_note": "Keyword triage only. No updated bound is certified automatically.",
              "records": records}
    (output / "manifest.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    (output / "papers.json").write_text(json.dumps(groups, indent=2, ensure_ascii=False) + "\n")
    with (output / "candidates.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["year", "title", "authors", "url", "source_type",
                                              "optimization_terms", "status"])
        writer.writeheader()
        for r in records:
            if r["optimization_terms"]:
                writer.writerow({k: "; ".join(r[k]) if k == "optimization_terms" else r[k]
                                 for k in writer.fieldnames})
    catalog = {"schemaVersion": "1.4", "catalogId": "cccg-optimization-survey",
               "title": "CCCG optimization-bound review leads", "contentUpdatedAt": finished,
               "generatedAt": finished, "problems": []}
    for r in groups:
        if not r["optimization_terms"]:
            continue
        key = hashlib.sha256(r["urls"][0].encode()).hexdigest()[:12]
        catalog["problems"].append({
            "recordId": f"lit:cccg-optimization-survey:{r['year']}-{key}",
            "problem": "Check whether modern optimization improves the bound in: " + r["title"],
            "contentUpdatedAt": finished, "comments": [], "status": "candidate_unreviewed",
            "source": {"title": r["title"], "authors": r["authors"], "url": r["urls"][0]},
            "sourceVersions": r["urls"],
            "tags": r["optimization_terms"],
            "verificationNotes": "Automatic keyword lead; theorem applicability and novelty not checked.",
        })
    catalog["problemCount"] = len(catalog["problems"])
    (output / "litchikin.json").write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "records"}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", nargs="+", type=int, default=[2005, 2006, 2007])
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache")
    parser.add_argument("--output", type=Path, default=ROOT / "results")
    parser.add_argument("--max-documents", type=int, default=0, help="0 means all discovered documents")
    args = parser.parse_args()
    if args.delay < 0.5 or args.max_documents < 0:
        parser.error("Use a delay of at least 0.5 seconds and a nonnegative document limit")
    for command in ("curl", "pdftotext"):
        if not shutil.which(command):
            parser.error(f"Missing required command: {command}")
    run(args)
