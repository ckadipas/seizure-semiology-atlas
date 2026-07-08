#!/usr/bin/env python3
"""Mechanical anti-fabrication gate.

For every finding in enrichment/corpus_findings.json, check that its recorded
`quote` (and the digits of its value) actually appear in the paper's raw source
text. A quote an agent could not have copied from the text did not come from the
text — it was invented or paraphrased beyond recognition. This turns "trust the
agent's quote" into "prove the quote exists".

The raw texts are copyrighted and NOT in the repo, so pass their directory:
    python3 tools/verify_quotes.py /path/to/corpus_in/txt

Because the source is OCR (messy: "88. 5%", "versién"), matching is done on a
normalization that strips all non-alphanumerics and lowercases, plus a
token-overlap fallback for OCR letter errors. Output categories:
  VERIFIED   - normalized quote is a substring of the normalized source
  LIKELY     - >=80% of the quote's words appear AND the value's digits appear
  UNVERIFIED - neither: the quote cannot be located in the text (treat as suspect)
"""
import json
import os
import re
import sys


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def digits(s):
    return re.findall(r"\d+", s or "")


def main():
    if len(sys.argv) < 2:
        print("usage: verify_quotes.py <txt_dir>")
        sys.exit(2)
    txt_dir = sys.argv[1]
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data = json.load(open(os.path.join(root, "enrichment", "corpus_findings.json")))

    cache = {}
    def source(fname):
        if fname not in cache:
            p = os.path.join(txt_dir, fname)
            cache[fname] = norm(open(p, encoding="utf-8", errors="ignore").read()) if os.path.exists(p) else None
        return cache[fname]

    tot = {"VERIFIED": 0, "LIKELY": 0, "UNVERIFIED": 0, "NO_SOURCE": 0}
    suspects = []
    per_paper = []

    for p in data["papers"]:
        src = source(p.get("file", ""))
        c = {"VERIFIED": 0, "LIKELY": 0, "UNVERIFIED": 0, "NO_SOURCE": 0}
        for f in p.get("findings", []):
            q = f.get("quote", "")
            if src is None:
                verdict = "NO_SOURCE"
            elif norm(q) and norm(q) in src:
                verdict = "VERIFIED"
            else:
                words = [w for w in re.findall(r"[a-z0-9]+", q.lower()) if len(w) >= 4]
                hit = sum(1 for w in words if w in src) / len(words) if words else 0
                val_ok = all(d in src for d in digits(str(f.get("value_text", "")))[:2]) if digits(str(f.get("value_text", ""))) else True
                verdict = "LIKELY" if (hit >= 0.8 and val_ok and words) else "UNVERIFIED"
            c[verdict] += 1
            tot[verdict] += 1
            if verdict == "UNVERIFIED":
                suspects.append({"cite": p.get("cite"), "phenomenon": f.get("phenomenon"),
                                 "value_text": f.get("value_text"), "quote": (q or "")[:140]})
        per_paper.append((p.get("cite", "?")[:40], c))

    n = sum(tot.values())
    print(f"=== quote verification over {n} findings ===")
    for k in ("VERIFIED", "LIKELY", "UNVERIFIED", "NO_SOURCE"):
        print(f"  {k:<10} {tot[k]:>4}  ({100*tot[k]/n:.1f}%)")
    print(f"\n=== {len(suspects)} UNVERIFIED (quote not locatable in source) ===")
    for s in suspects[:60]:
        print(f"  [{s['cite']}] {s['phenomenon']} = {s['value_text']}")
        print(f"      quote: {s['quote']}")
    out = os.path.join(root, "enrichment", "quote_audit.json")
    json.dump({"totals": tot, "suspects": suspects}, open(out, "w"), indent=1)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
