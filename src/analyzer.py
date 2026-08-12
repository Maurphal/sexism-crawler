# -*- coding: utf-8 -*-
"""
Πυρήνας ανίχνευσης μη-συμπεριληπτικής / σεξιστικής γλώσσας.

Πιστό port της λογικής analyzeText() από το sexism-tracker-v10-offline.html
(βλ. buildBoundaryRegex, getClauseBounds, isAlreadyInclusive, findMatches,
findGenericParticipleMatches). Η μόνη ουσιαστική διαφορά: η JS χρησιμοποιεί
\\p{L} (Unicode "γράμμα") στα regex· η Python built-in `re` δεν το υποστηρίζει,
οπότε χρησιμοποιούμε το ισοδύναμο idiom:

    LETTER     = [^\\W\\d_]   ->  "γράμμα οποιασδήποτε γλώσσας" (≈ \\p{L})
    NOT_LETTER = [\\W\\d_]    ->  "οτιδήποτε ΔΕΝ είναι γράμμα"

Δοκιμασμένο με ελληνικά (πεζά/κεφαλαία, τονισμένα φωνήεντα) — δεν χρειάζεται
το πακέτο `regex` ούτε καμία άλλη εξωτερική εξάρτηση.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Callable

from . import rules_data as R

LETTER = r"[^\W\d_]"
NOT_LETTER = r"[\W\d_]"

_boundary_cache: dict[str, re.Pattern] = {}
_clause_boundary_re = re.compile(r"[.!;]|(?:\r?\n[ \t]*){2,}")
_slash_marker_re = re.compile(
    LETTER + r"+/(ή|ές|α|ας|ες|η|ης|ισσα|ισσας|ισσες|τρια|τριας|τριες)"
    rf"(?:(?={NOT_LETTER})|$)",
    re.IGNORECASE,
)
_self_reference_re = re.compile(
    rf"(?:(?<=^)|(?<={NOT_LETTER}))(ο\s+ίδιος|η\s+ίδια)(?:(?={NOT_LETTER})|$)",
    re.IGNORECASE,
)
_generic_participle_re = re.compile(
    rf"(?:(?<=^)|(?<={NOT_LETTER}))({LETTER}{{2,}}?)(όμεν|ούμεν)(ος|ου|ο|οι|ων|ους)"
    rf"(?:(?={NOT_LETTER})|$)",
    re.IGNORECASE,
)


@dataclass
class Match:
    start_index: int
    end_index: int
    matched_string: str
    rule: dict = field(default_factory=dict)
    id: str = field(default_factory=lambda: "match-" + uuid.uuid4().hex[:9])


def _boundary_regex(alternation: str) -> re.Pattern:
    """Ισοδύναμο buildBoundaryRegex(): (?<=^|non-letter)(alt)(?=non-letter|$)."""
    cached = _boundary_cache.get(alternation)
    if cached is None:
        pattern = (
            rf"(?:(?<=^)|(?<={NOT_LETTER}))({alternation})(?:(?={NOT_LETTER})|$)"
        )
        cached = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
        _boundary_cache[alternation] = cached
    return cached


def get_clause_bounds(text: str, idx: int) -> tuple[int, int]:
    """Όρια της 'πρότασης' γύρω από το idx: στίξη (. ! ;) ή αλλαγή παραγράφου."""
    start = 0
    end = len(text)
    for m in _clause_boundary_re.finditer(text):
        boundary_end = m.end()
        if boundary_end <= idx:
            start = boundary_end
        if m.start() >= idx:
            end = m.start()
            break
    return start, end


def has_generic_slash_marker(clause_text: str) -> bool:
    """π.χ. 'Ακαδημαϊκοί/ές', 'φοιτητής/τρια' — ήδη σημειωμένο και τα δύο γένη."""
    return bool(_slash_marker_re.search(clause_text))


def has_self_reference_marker(clause_text: str) -> bool:
    """'ο ίδιος' / 'η ίδια' -> αναφορά σε ήδη κατονομασμένο πρόσωπο."""
    return bool(_self_reference_re.search(clause_text))


def is_already_inclusive(raw_text: str, start_index: int, fem_patterns) -> bool:
    start, end = get_clause_bounds(raw_text, start_index)
    clause = raw_text[start:end]
    if has_generic_slash_marker(clause):
        return True
    if has_self_reference_marker(clause):
        return True
    if not fem_patterns:
        return False
    for p in fem_patterns:
        try:
            if re.search(p, clause, re.IGNORECASE):
                return True
        except re.error:
            continue
    return False


def find_matches(raw_text: str, word: str, fem_patterns, meta) -> list[Match]:
    results: list[Match] = []
    try:
        regex = _boundary_regex(word)
    except re.error:
        return results
    for m in regex.finditer(raw_text):
        start_index = m.start()
        end_index = m.end()
        if not is_already_inclusive(raw_text, start_index, fem_patterns):
            rule = meta(m.group(0)) if callable(meta) else meta
            results.append(
                Match(
                    start_index=start_index,
                    end_index=end_index,
                    matched_string=m.group(0),
                    rule=rule,
                )
            )
    return results


def find_generic_participle_matches(raw_text: str) -> list[Match]:
    """Μορφολογικός κανόνας: αρσενικές μετοχές σε -όμενος/-ούμενος."""
    results: list[Match] = []
    for m in _generic_participle_re.finditer(raw_text):
        full = m.group(0)
        stem, root, ending = m.group(1), m.group(2), m.group(3)
        start_index = m.start()
        end_index = m.end()
        fem_ending = R.MASC_TO_FEM_PARTICIPLE_ENDING.get(ending, "η")
        fem_form = f"{stem}{root}{fem_ending}"
        fem_check = [rf"{re.escape(stem)}{re.escape(root)}(η|ης|ες)"]

        if not is_already_inclusive(raw_text, start_index, fem_check):
            results.append(
                Match(
                    start_index=start_index,
                    end_index=end_index,
                    matched_string=full,
                    rule={
                        "title": "Αρσενική Μετοχή (κατηγορία -όμενος)",
                        "type": "generic",
                        "suggestion": f"{full} και {fem_form}",
                        "desc": (
                            "Αυτόματος εντοπισμός βάσει μορφολογικού μοτίβου "
                            "(μετοχή σε -όμενος/-ούμενος), όχι από προκαθορισμένη "
                            "λίστα λέξεων. Ελέγξτε αν αναφέρεται σε μεικτό "
                            "πληθυσμό και προσθέστε το θηλυκό γένος ή "
                            "χρησιμοποιήστε ουδέτερη διατύπωση (π.χ. «το "
                            "ενδιαφερόμενο άτομο»)."
                        ),
                    },
                )
            )
    return results


def analyze_text(raw_text: str) -> list[Match]:
    """Πλήρες port του analyzeText(): τρέχει όλες τις οικογένειες κανόνων,
    ταξινομεί τα ευρήματα και αφαιρεί τυχόν επικαλύψεις (κρατά το πρώτο/
    μεγαλύτερο εύρημα σε κάθε σημείο, ακριβώς όπως η JS)."""
    matches: list[Match] = []

    for group in R.ROLE_WORD_GROUPS:
        for form in group["forms"]:
            desc = (
                "Γενικευτική χρήση του αρσενικού γένους για μεικτό πληθυσμό. "
                "Προτείνεται ταυτόχρονη αναφορά και στα δύο γραμματικά γένη."
            )
            if group.get("neutralAlt"):
                desc += f' Εναλλακτικά (ουδέτερος όρος): «{group["neutralAlt"]}».'
            meta = {
                "title": group["title"],
                "type": "generalization",
                "suggestion": f'{form["m"]} και {form["f"]}',
                "desc": desc,
            }
            matches += find_matches(raw_text, form["m"], group.get("femCheck"), meta)

    for group in R.ADJECTIVE_GROUPS:
        for form in group["forms"]:
            meta = {
                "title": group["title"],
                "type": "generalization",
                "suggestion": f'{form["m"]} και {form["f"]}',
                "desc": R.ADJECTIVE_GROUP_DESC,
            }
            matches += find_matches(raw_text, form["m"], group.get("femCheck"), meta)

    for rule in R.PRONOUN_WORDS:
        meta = {
            "title": "Αντωνυμία Γενικευτικής Χρήσης",
            "type": "pronoun",
            "suggestion": rule["suggestion"],
            "desc": rule["desc"] + " (Ελέγξτε αν όντως αναφέρεται σε μεικτό πληθυσμό.)",
        }
        matches += find_matches(raw_text, rule["pattern"], None, meta)

    for rule in R.REPLACE_WORDS:
        for word in rule["pattern"].split("|"):
            meta = {
                "title": rule["title"],
                "type": "replace",
                "suggestion": rule["suggestion"],
                "desc": rule["desc"],
            }
            matches += find_matches(raw_text, word, None, meta)

    for rule in R.STEREOTYPE_WORDS:
        for word in rule["pattern"].split("|"):
            meta = {
                "title": rule["title"],
                "type": "stereotype",
                "suggestion": rule["suggestion"],
                "desc": rule["desc"],
            }
            matches += find_matches(raw_text, word, None, meta)

    for rule in R.PROFESSION_SUFFIX_WORDS:
        for word in rule["pattern"].split("|"):
            meta = {
                "title": rule["title"],
                "type": "profession",
                "suggestion": rule["suggestion"],
                "desc": rule["desc"],
            }
            matches += find_matches(raw_text, word, None, meta)

    # Ο γενικός μορφολογικός κανόνας τρέχει τελευταίος, ώστε -αν συμπέσει
    # με ήδη καταχωρημένο ζεύγος λέξεων- να προτιμηθεί η ακριβέστερη
    # καταχωρημένη πρόταση (βλ. φιλτράρισμα επικαλύψεων παρακάτω).
    matches += find_generic_participle_matches(raw_text)

    for rule in R.COMPOUND_TITLE_WORDS:
        meta = {
            "title": rule["title"],
            "type": "generalization",
            "suggestion": rule["suggestion"],
            "desc": rule["desc"],
        }
        matches += find_matches(raw_text, rule["pattern"], rule.get("femCheck"), meta)

    matches.sort(key=lambda m: (m.start_index, -(m.end_index - m.start_index)))

    filtered: list[Match] = []
    last_end = -1
    for match in matches:
        if match.start_index >= last_end:
            filtered.append(match)
            last_end = match.end_index
    return filtered
