# Sexism Crawler

Python crawler που σαρώνει συγκεκριμένες ιστοσελίδες και εντοπίζει
μη-συμπεριληπτική / σεξιστική ελληνική γλώσσα (γενικευτικό αρσενικό γένος,
μειωτικές καταλήξεις, στερεότυπα κ.λπ.). Οι κανόνες εντοπισμού είναι πιστό
port της λογικής από το `sexism-tracker-v10-offline.html`.

## Πώς δουλεύει

1. Διαβάζει τη λίστα σελίδων από `config/sites.yaml`.
2. Για κάθε σελίδα: ελέγχει το `robots.txt` της (σέβεται πάντα τους
   κανόνες/απαγορεύσεις), κατεβάζει το HTML, εξάγει το ορατό κείμενο
   (χωρίς menus/scripts) και τρέχει την ανάλυση.
3. Αποθηκεύει τα αποτελέσματα στο `results/latest.json`. Επειδή αυτό το
   αρχείο μπαίνει σε commit σε κάθε σάρωση, το **ιστορικό σαρώσεων
   προκύπτει αυτόματα από το git log** — δεν χρειάζεται ξεχωριστή βάση
   δεδομένων.
4. Παράγει μια στατική αναφορά `docs/index.html`, έτοιμη για δημοσίευση
   με GitHub Pages.
5. Ένα scheduled GitHub Actions workflow (`.github/workflows/scan.yml`)
   τρέχει τα παραπάνω αυτόματα κάθε Δευτέρα (ή όποτε θες, χειροκίνητα από
   το tab "Actions").

## Ρύθμιση

1. **Πρόσθεσε τις σελίδες σου** στο `config/sites.yaml`.
2. **Άλλαξε το User-Agent** στο `src/fetcher.py` (`USER_AGENT`) ώστε να
   δείχνει στο δικό σου repo — έτσι όποιος δει τα logs του site του
   ξέρει ποιος/τι τον επισκέφθηκε.
3. (Προαιρετικό) **Ενεργοποίησε GitHub Pages**: Settings → Pages →
   Source: `Deploy from a branch` → Branch: `main`, folder: `/docs`. Η
   αναφορά θα είναι διαθέσιμη σε `https://<username>.github.io/<repo>/`.
4. Κάνε push το repo στο GitHub — το workflow θα ξεκινήσει να τρέχει
   αυτόματα σύμφωνα με το cron schedule.

## Τοπική εκτέλεση

```bash
pip install -r requirements.txt
python -m src.crawler   # σαρώνει και γράφει results/latest.json
python -m src.report    # παράγει docs/index.html
python tests/test_analyzer.py   # γρήγορο smoke test της λογικής ανάλυσης
```

## Ηθική/νομική σημείωση για το scraping

Ο crawler **σέβεται πάντα** το `robots.txt` κάθε σελίδας — αν μια σελίδα
το απαγορεύει ρητά, παραλείπεται αυτόματα και καταγράφεται ως τέτοια στα
αποτελέσματα. Κρατάει επίσης καθυστέρηση ανάμεσα σε requests προς το ίδιο
domain (default 3 δευτερόλεπτα, ή όσο λέει το `Crawl-delay` του
robots.txt αν υπάρχει). Αν οι σελίδες που θες να σαρώσεις είναι δικές
σου, μπορείς προαιρετικά να προσθέσεις ρητή εγγραφή `Allow` στο δικό
τους robots.txt για το User-Agent του crawler — δεν είναι υποχρεωτικό,
απλώς πιο ρητό.

## Δομή project

```
config/sites.yaml         λίστα σελίδων προς σάρωση
src/rules_data.py         δεδομένα κανόνων (λέξεις, προτάσεις) — πορταρισμένα από το .html
src/analyzer.py           η ίδια η λογική ανίχνευσης (analyze_text κ.λπ.)
src/fetcher.py            robots.txt-aware fetching + εξαγωγή κειμένου
src/crawler.py            orchestration: διαβάζει sites.yaml, σαρώνει, αποθηκεύει
src/report.py             παράγει το docs/index.html
results/latest.json       τελευταία αποτελέσματα (ιστορικό = git log αυτού του αρχείου)
docs/index.html           η στατική αναφορά (GitHub Pages)
.github/workflows/scan.yml   το scheduled workflow
```
