# -*- coding: utf-8 -*-
"""
Παράγει ένα αυτόνομο, στατικό docs/index.html από το results/latest.json —
έτοιμο για δημοσίευση με GitHub Pages (Settings -> Pages -> branch: main,
folder: /docs). Δεν χρησιμοποιεί CDN/εξωτερικές εξαρτήσεις, ώστε να ανοίγει
παντού χωρίς σύνδεση στο internet.

Εκτέλεση:  python -m src.report
"""
from __future__ import annotations

import json
from datetime import datetime
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS_FILE = ROOT / "results" / "latest.json"
OUTPUT_FILE = ROOT / "docs" / "index.html"

CATEGORY_LABELS = {
    "generalization": "Γενικευτικό Αρσενικό",
    "pronoun": "Αντωνυμία",
    "replace": "Προτεινόμενη Αντικατάσταση",
    "stereotype": "Στερεότυπο",
    "profession": "Μειωτική Κατάληξη Επαγγέλματος",
    "generic": "Μορφολογικός Κανόνας",
}

STYLE = """
body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:900px;
margin:2rem auto;padding:0 1rem;color:#1e293b;background:#f8fafc}
h1{font-size:1.5rem}
.meta{color:#64748b;font-size:.9rem;margin-bottom:2rem}
.site{background:#fff;border:1px solid #e2e8f0;border-radius:.75rem;
padding:1.25rem 1.5rem;margin-bottom:1rem}
.site-header{display:flex;justify-content:space-between;align-items:center;
flex-wrap:wrap;gap:.5rem}
.site-header a{color:#7c3aed;text-decoration:none;font-weight:600}
.badge{font-size:.75rem;font-weight:600;padding:.15rem .6rem;border-radius:999px}
.badge-clean{background:#dcfce7;color:#166534}
.badge-found{background:#fee2e2;color:#991b1b}
.badge-error{background:#fef3c7;color:#92400e}
.finding{border-top:1px solid #f1f5f9;padding-top:.6rem;margin-top:.6rem}
.finding .word{font-weight:700;color:#be185d}
.finding .cat{font-size:.7rem;text-transform:uppercase;letter-spacing:.05em;
color:#7c3aed}
.finding .suggestion{color:#166534;font-size:.9rem}
.finding .desc{color:#475569;font-size:.85rem}
.scanned-at{color:#94a3b8;font-size:.8rem}
"""


def render() -> str:
    if not RESULTS_FILE.exists():
        data = {"run_started_at": None, "sites_scanned": 0,
                "total_findings": 0, "results": []}
    else:
        data = json.loads(RESULTS_FILE.read_text(encoding="utf-8"))

    parts = [
        "<!DOCTYPE html><html lang='el'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width, initial-scale=1'>",
        "<title>Αναφορά Συμπεριληπτικής Γλώσσας</title>",
        f"<style>{STYLE}</style></head><body>",
        "<h1>Αναφορά Συμπεριληπτικής / Μη-Σεξιστικής Γλώσσας</h1>",
    ]

    run_at = data.get("run_started_at")
    if run_at:
        try:
            run_at = datetime.fromisoformat(run_at).strftime("%d/%m/%Y %H:%M UTC")
        except ValueError:
            pass
    parts.append(
        f"<p class='meta'>Τελευταία σάρωση: {escape(str(run_at))} &middot; "
        f"{data.get('sites_scanned', 0)} σελίδες &middot; "
        f"{data.get('total_findings', 0)} συνολικά ευρήματα</p>"
    )

    for site in data.get("results", []):
        label = escape(site.get("label", site.get("url", "")))
        url = escape(site.get("url", ""))
        scanned_at = site.get("scanned_at", "")
        try:
            scanned_at = datetime.fromisoformat(scanned_at).strftime("%d/%m/%Y %H:%M UTC")
        except ValueError:
            pass

        parts.append("<div class='site'><div class='site-header'>")
        parts.append(f"<a href='{url}' target='_blank' rel='noopener'>{label}</a>")

        if not site.get("ok"):
            parts.append("<span class='badge badge-error'>Σφάλμα</span>")
            parts.append("</div>")
            parts.append(f"<p class='desc'>{escape(site.get('error', ''))}</p>")
        else:
            count = site.get("findings_count", 0)
            if count == 0:
                parts.append("<span class='badge badge-clean'>Καθαρό</span>")
            else:
                parts.append(f"<span class='badge badge-found'>{count} ευρήματα</span>")
            parts.append("</div>")
            parts.append(f"<div class='scanned-at'>Σαρώθηκε: {escape(str(scanned_at))}</div>")

            for finding in site.get("findings", []):
                cat = CATEGORY_LABELS.get(finding.get("category"), finding.get("category", ""))
                parts.append("<div class='finding'>")
                parts.append(f"<span class='cat'>{escape(cat)}</span> — ")
                parts.append(f"<span class='word'>{escape(finding.get('matched_text', ''))}</span>")
                parts.append(f"<div class='desc'>{escape(finding.get('description', ''))}</div>")
                if finding.get("suggestion"):
                    parts.append(
                        f"<div class='suggestion'>Πρόταση: {escape(finding['suggestion'])}</div>"
                    )
                parts.append("</div>")

        parts.append("</div>")

    parts.append("</body></html>")
    return "".join(parts)


def main() -> None:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(render(), encoding="utf-8")
    print(f"Report: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
