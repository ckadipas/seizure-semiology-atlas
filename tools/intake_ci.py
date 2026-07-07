#!/usr/bin/env python3
"""
intake_ci.py — automated PDF paper intake (runs in GitHub Actions).

Primary intake route. Given an intake issue that has a PDF attached, this:
  1. finds the PDF attachment URL in the issue body and downloads it (the
     runner can reach GitHub attachments; a session sandbox cannot),
  2. sends the PDF to Claude (claude-opus-4-8) with the atlas's sign list and
     paper library as context, asking for short, attributed, PAGE-CITED
     findings that bear on localizing/lateralizing semiology,
  3. appends the validated findings to enrichment/intake_findings.json.

The full PDF / full text is NEVER committed — only the derived short factual
extractions with their source page. The workflow then rebuilds enrichment.json,
runs the provenance + validation gates, and opens a PR the owner approves.

Requires ANTHROPIC_API_KEY in the environment. The paper's DOI/PubMed record is
the fallback route (web search) when no PDF is attached.
"""
import base64
import json
import os
import re
import sys
import urllib.request

import anthropic


def _find_root(start):
    d = os.path.dirname(os.path.abspath(start))
    while True:
        if os.path.exists(os.path.join(d, ".atlas-root")):
            return d
        p = os.path.dirname(d)
        if p == d:
            return os.path.dirname(os.path.abspath(start))
        d = p


ROOT = _find_root(__file__)
MODEL = os.environ.get("INTAKE_MODEL", "claude-opus-4-8")

# Structured-output schema: papers to add + page-cited findings. Every finding
# must carry a page (`pg`); check_provenance.py enforces it downstream too.
SCHEMA = {
    "type": "object",
    "properties": {
        "papers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "cite": {"type": "string"},
                    "journal": {"type": "string"},
                    "title": {"type": "string"},
                    "contribution": {"type": "string"},
                },
                "required": ["cite", "journal", "title", "contribution"],
                "additionalProperties": False,
            },
        },
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "sign_stem": {"type": "string"},
                    "paper": {"type": "string"},
                    "finding": {"type": "string"},
                    "pg": {"type": "string"},
                },
                "required": ["sign_stem", "paper", "finding", "pg"],
                "additionalProperties": False,
            },
        },
        "notes": {"type": "string"},
    },
    "required": ["papers", "findings", "notes"],
    "additionalProperties": False,
}


def find_pdf_url(body):
    m = re.search(r"https?://[^\s)<>\]]+\.pdf", body or "")
    return m.group(0) if m else None


def main():
    body = os.environ.get("ISSUE_BODY", "")
    title = os.environ.get("ISSUE_TITLE", "")
    url = find_pdf_url(body)
    if not url:
        print("No PDF attachment found in the issue body — skipping the PDF route "
              "(submit a DOI/PubMed link for the web-search fallback, or attach a PDF).")
        return

    print(f"Downloading attachment: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "seizure-atlas-intake"})
    pdf = urllib.request.urlopen(req, timeout=90).read()
    b64 = base64.standard_b64encode(pdf).decode("ascii")
    print(f"  {len(pdf)} bytes")

    signs = json.load(open(os.path.join(ROOT, "data", "semiology_data.json")))
    names = sorted({s["sign"] for s in signs})
    papers = json.load(open(os.path.join(ROOT, "enrichment", "enrichment.json")))["papers"]
    lib = sorted({p[0] for p in papers})

    system = (
        "You integrate epilepsy-semiology papers into a source-grounded, educational atlas. "
        "Extract ONLY short, attributed factual findings that bear on LOCALIZING or LATERALIZING "
        "seizure semiology. Each finding must be one or two sentences, paraphrased in your own words "
        "(never a long verbatim quote), include the reported figure/percentage/N when the paper gives "
        "one, and record the SOURCE PAGE it appears on in `pg` (e.g. 'p.608' or 'pp.606-611'). "
        "Attach each finding to an existing sign by choosing `sign_stem`: a short lowercase substring "
        "of one of the atlas sign names provided. If the paper is not already in the library, add it "
        "under `papers`. Preserve the atlas's discipline: prefer disciplined primary series with an "
        "explicit ground truth; treat literature-mined meta-analyses skeptically; never fabricate a "
        "figure; if the paper does not actually support a claim, omit it. Use `notes` to answer any "
        "questions the submitter asked and to flag anything uncertain. Do not reproduce long passages."
    )
    user_text = (
        f"Issue title: {title}\n\n"
        f"Submitter instructions:\n{body}\n\n"
        "Existing sign names (choose each sign_stem as a substring of one of these):\n- "
        + "\n- ".join(names)
        + "\n\nPapers already in the library (do NOT re-add these):\n- "
        + "\n- ".join(lib)
        + "\n\nReturn short, page-cited findings only."
    )

    client = anthropic.Anthropic()
    with client.messages.stream(
        model=MODEL,
        max_tokens=8000,
        thinking={"type": "adaptive"},
        system=system,
        messages=[{"role": "user", "content": [
            {"type": "document", "source": {
                "type": "base64", "media_type": "application/pdf", "data": b64}},
            {"type": "text", "text": user_text},
        ]}],
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
    ) as stream:
        msg = stream.get_final_message()

    text = next(b.text for b in msg.content if b.type == "text")
    result = json.loads(text)

    path = os.path.join(ROOT, "enrichment", "intake_findings.json")
    store = json.load(open(path)) if os.path.exists(path) else {}
    store.setdefault("papers", [])
    store.setdefault("findings", [])

    seen_papers = {p.get("cite") for p in store["papers"]} | set(lib)
    for p in result.get("papers", []):
        if p.get("cite") and p["cite"] not in seen_papers:
            store["papers"].append(p)
            seen_papers.add(p["cite"])

    seen_findings = {(f.get("paper"), f.get("finding")) for f in store["findings"]}
    added = 0
    for f in result.get("findings", []):
        key = (f.get("paper"), f.get("finding"))
        if all(f.get(k) for k in ("sign_stem", "paper", "finding", "pg")) and key not in seen_findings:
            store["findings"].append(f)
            seen_findings.add(key)
            added += 1

    with open(path, "w") as out:
        json.dump(store, out, indent=1, ensure_ascii=False)
        out.write("\n")

    print(f"Integrated {added} page-cited finding(s).")
    if result.get("notes"):
        print("Notes:", result["notes"][:600])


if __name__ == "__main__":
    main()
