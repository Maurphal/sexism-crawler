# -*- coding: utf-8 -*-
"""
Κύριο script: διαβάζει config/sites.yaml, σαρώνει κάθε σελίδα (σεβόμενο
robots.txt), τρέχει την ανάλυση, και αποθηκεύει τα αποτελέσματα σε
results/latest.json. Η ιστορία των σαρώσεων προκύπτει αυτόματα από το
git history του αρχείου (κάθε commit = μία σάρωση σε συγκεκριμένη ημερομηνία) —
δεν χρειάζεται ξεχωριστή βάση δεδομένων.

Εκτέλεση:  python -m src.crawler
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from . import fetcher
from .analyzer import analyze_text

ROOT = Path(__file__).resolve().parent.parent
SITES_FILE = ROOT / "config" / "sites.yaml"
RESULTS_FILE = ROOT / "results" / "latest.json"


def load_sites() -> list[dict]:
    if not SITES_FILE.exists():
        print(f"Δεν βρέθηκε το {SITES_FILE}", file=sys.stderr)
        return []
    with open(SITES_FILE, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("sites", [])


def scan_site(site: dict) -> dict:
    url = site["url"]
    label = site.get("label", url)
    print(f"-> Σάρωση: {label} ({url})")

    result = fetcher.fetch(url)
    scanned_at = datetime.now(timezone.utc).isoformat()

    if not result.ok:
        return {
            "url": url,
            "label": label,
            "scanned_at": scanned_at,
            "ok": False,
            "error": result.error,
            "skipped_by_robots": result.skipped_by_robots,
            "findings": [],
        }

    matches = analyze_text(result.text)
    findings = [
        {
            "matched_text": m.matched_string,
            "category": m.rule.get("type"),
            "title": m.rule.get("title"),
            "suggestion": m.rule.get("suggestion"),
            "description": m.rule.get("desc"),
        }
        for m in matches
    ]

    return {
        "url": url,
        "label": label,
        "scanned_at": scanned_at,
        "ok": True,
        "text_length": len(result.text),
        "findings_count": len(findings),
        "findings": findings,
    }


def main() -> None:
    sites = load_sites()
    if not sites:
        print("Δεν υπάρχουν σελίδες στο config/sites.yaml — πρόσθεσε τουλάχιστον μία.")
        return

    run_started_at = datetime.now(timezone.utc).isoformat()
    results = [scan_site(site) for site in sites]

    output = {
        "run_started_at": run_started_at,
        "sites_scanned": len(results),
        "total_findings": sum(r.get("findings_count", 0) for r in results),
        "results": results,
    }

    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nΟλοκληρώθηκε: {output['sites_scanned']} σελίδες, "
          f"{output['total_findings']} συνολικά ευρήματα.")
    print(f"Αποτελέσματα: {RESULTS_FILE}")


if __name__ == "__main__":
    main()
