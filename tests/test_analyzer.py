# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.analyzer import analyze_text

SAMPLE = (
    "Ενημερώνουμε τους φοιτητές του Πανεπιστημίου ότι η παροχή πληροφορίας "
    "θα δίδεται αποκλειστικά στον αιτούντα φοιτητή."
)


def test_finds_masculine_generic_role_noun():
    matches = analyze_text(SAMPLE)
    words = [m.matched_string for m in matches]
    assert "φοιτητές" in words
    assert "αιτούντα" in words


def test_does_not_flag_already_inclusive_slash_form():
    text = "Καλωσορίζουμε τους/τις φοιτητές/τριες του τμήματος."
    matches = analyze_text(text)
    # Το "τριες" markers στην ίδια πρόταση πρέπει να καταστείλει το εύρημα.
    flagged_words = [m.matched_string for m in matches]
    assert "φοιτητές" not in flagged_words


def test_generic_participle_rule():
    text = "Κάθε ενδιαφερόμενος καλείται να υποβάλει αίτηση."
    matches = analyze_text(text)
    assert any(m.matched_string == "ενδιαφερόμενος" for m in matches)


if __name__ == "__main__":
    test_finds_masculine_generic_role_noun()
    test_does_not_flag_already_inclusive_slash_form()
    test_generic_participle_rule()
    print("Όλα τα tests πέρασαν.")
