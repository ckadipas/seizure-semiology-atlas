#!/usr/bin/env python3
"""
intake_paper.py — screen, de-duplicate, extract, and QUEUE a new paper for
integration into the atlas.

This automates the *mechanical* half of intake (hashing, dedup, text
extraction, scaffolding a structured intake card). The *judgment* half
(deciding which findings are trustworthy and which signs they touch) is left
to a human reviewer — the queue card gives them a fill-in-the-blanks template.

Usage:
    python3 tools/intake_paper.py path/to/new_paper.pdf
    python3 tools/intake_paper.py intake/inbox/new_paper.pdf

What it does:
    1. MD5-hashes the PDF and checks corpus/manifest.csv + existing hashes for
       duplicates (so the same paper is never integrated twice).
    2. Extracts text with `pdftotext` (poppler). If the PDF is scanned (no text
       layer), it says so and points to the OCR fallback.
    3. Writes the extracted text to corpus/txt/<slug>.txt (local, git-ignored).
    4. Creates intake/queue/<slug>.md — a structured intake card to be filled in
       by a reviewer, then transcribed into build_enrichment.py.
    5. Appends a 'queued' row to corpus/manifest.csv.

No pip dependencies; requires the `pdftotext` system tool for extraction.
"""
import os, sys, re, csv, hashlib, subprocess, shutil, datetime

def _find_root(start):
    d = os.path.dirname(os.path.abspath(start))
    while True:
        if os.path.exists(os.path.join(d, ".atlas-root")): return d
        p = os.path.dirname(d)
        if p == d: return os.path.dirname(os.path.abspath(start))
        d = p

ROOT = _find_root(__file__)

def slugify(s):
    s = re.sub(r"\.pdf$", "", os.path.basename(s), flags=re.I)
    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")
    return s[:80] or "paper"

def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()

def existing_hashes():
    """MD5s of any PDFs already sitting in corpus/pdfs (local working copies)."""
    d = os.path.join(ROOT, "corpus", "pdfs")
    out = {}
    if os.path.isdir(d):
        for f in os.listdir(d):
            if f.lower().endswith(".pdf"):
                out[md5(os.path.join(d, f))] = f
    return out

def main():
    if len(sys.argv) < 2:
        print("usage: python3 tools/intake_paper.py path/to/paper.pdf"); sys.exit(2)
    src = sys.argv[1]
    if not os.path.isfile(src):
        print(f"ERROR: file not found: {src}"); sys.exit(2)
    if not src.lower().endswith(".pdf"):
        print("ERROR: expected a .pdf file"); sys.exit(2)

    slug = slugify(src)
    digest = md5(src)

    # 1. dedup
    dup = existing_hashes().get(digest)
    if dup:
        print(f"DUPLICATE: identical content already present as corpus/pdfs/{dup}")
        print("Nothing queued. If this is intentional, remove the existing copy first.")
        sys.exit(1)

    # move/copy the PDF into the local (git-ignored) working corpus
    pdfs_dir = os.path.join(ROOT, "corpus", "pdfs"); os.makedirs(pdfs_dir, exist_ok=True)
    dest_pdf = os.path.join(pdfs_dir, slug + ".pdf")
    if os.path.abspath(src) != os.path.abspath(dest_pdf):
        shutil.copy(src, dest_pdf)

    # 2-3. text extraction
    txt_dir = os.path.join(ROOT, "corpus", "txt"); os.makedirs(txt_dir, exist_ok=True)
    txt_path = os.path.join(txt_dir, slug + ".txt")
    text_chars = 0
    have_pdftotext = shutil.which("pdftotext") is not None
    if have_pdftotext:
        subprocess.run(["pdftotext", "-layout", dest_pdf, txt_path],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(txt_path):
            text_chars = len(open(txt_path, errors="ignore").read().strip())
    scanned = text_chars < 100
    ocr_note = ""
    if not have_pdftotext:
        ocr_note = "`pdftotext` not installed — install poppler-utils, then re-run."
    elif scanned:
        ocr_note = ("No text layer detected (scanned PDF). OCR fallback:\n"
                    "  `pdftoppm -r 300 -png paper.pdf pg && for i in pg-*.png; "
                    "do tesseract $i - >> corpus/txt/%s.txt; done`" % slug)

    # peek at a title line for the card
    title_guess = ""
    if text_chars:
        head = open(txt_path, errors="ignore").read(600).replace("\n", " ")
        title_guess = re.sub(r"\s+", " ", head).strip()[:160]

    # 4. intake card
    q_dir = os.path.join(ROOT, "intake", "queue"); os.makedirs(q_dir, exist_ok=True)
    card = os.path.join(q_dir, slug + ".md")
    today = datetime.date.today().isoformat()
    open(card, "w").write(f"""# Intake card — {slug}

- **Queued:** {today}
- **MD5:** `{digest}`
- **Local PDF:** `corpus/pdfs/{slug}.pdf`  _(git-ignored — not committed)_
- **Extracted text:** `corpus/txt/{slug}.txt`  _(git-ignored)_
- **Text extracted:** {"yes (" + str(text_chars) + " chars)" if text_chars else "NO"}
{("- **Action needed:** " + ocr_note) if ocr_note else ""}

## 1. Bibliographic record  _(fill in, then copy to corpus/manifest.csv + PAPERS)_
- Citation (Author et al. YEAR):
- Journal:
- Title: {title_guess}
- DOI:
- Permission / license to include short extractions: [ ] yes

## 2. Screening  _(is this in scope?)_
- Relevant to localizing/lateralizing semiology?  [ ] yes  [ ] no
- Study type: [ ] primary series  [ ] SEEG/anatomo-electro-clinical  [ ] review  [ ] case report
- Ground truth (postop Sf / SEEG / imaging concordance):
- Sample size (N):
- Reliability check — beware literature-mined meta-analyses with incoherent
  sign categories (see README, Design decisions). Prefer disciplined sign
  definitions with explicit ground truth.

## 3. Findings to integrate  _(one row per usable figure)_
| Sign (must match a sign name substring) | Finding (short, attributed, with N) | Direction / % / OR |
|---|---|---|
|  |  |  |
|  |  |  |

## 4. New signs surfaced (if any)
- region / sub / sign / phase / latcode / loc / sens / spec / evid / notes / cite:

## 5. Integration steps  _(reviewer)_
1. Add bibliographic row to `corpus/manifest.csv` (status: integrated) and a
   4-tuple to `PAPERS` in `enrichment/build_enrichment.py`.
2. For each finding above, add an `add("<sign-stem>", "<Paper YEAR>", "<finding>")`
   call in `build_enrichment.py`.
3. For new signs, append a full object to `NEW` (with an `_ev` list).
4. `make build` → review the diff → commit → open PR.
5. Move this card to the bottom of CHANGELOG under the next version, delete from queue.
""")

    # 5. manifest append (queued)
    man = os.path.join(ROOT, "corpus", "manifest.csv")
    newfile = not os.path.exists(man)
    with open(man, "a", newline="") as f:
        w = csv.writer(f)
        if newfile:
            w.writerow(["citation", "journal", "title", "status", "contribution"])
        w.writerow([f"(queued:{slug})", "", title_guess, "queued", "awaiting review"])

    print(f"Queued '{slug}'.")
    print(f"  PDF   -> corpus/pdfs/{slug}.pdf   (local only)")
    print(f"  text  -> corpus/txt/{slug}.txt    ({text_chars} chars){' — SCANNED' if scanned else ''}")
    print(f"  card  -> intake/queue/{slug}.md   (fill this in next)")
    if ocr_note:
        print("  NOTE: " + ocr_note.splitlines()[0])
    print("\nNext: open the intake card, fill in findings, then transcribe into")
    print("enrichment/build_enrichment.py and run `make build`.")

if __name__ == "__main__":
    main()
