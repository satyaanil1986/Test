import json
import os
import re

from anthropic import Anthropic

from . import docx_clauses

SYSTEM_PROMPT = """You are acting as an experienced real estate/HOA lawyer reviewing owner
comments on a draft apartment-association bye-laws document for an
Indian apartment owners' association (governed by the Karnataka
Apartment Ownership Act, 1972). For each owner comment, given the
relevant clause text from the bye-laws, produce: (1) a short category
label, (2) a `status` of "fix" if the comment identifies a genuine
drafting error/contradiction that should be corrected in the document,
or "flagged" if it's a policy question, clarification request, or
judgment call that needs a committee/AGM decision, (3) a concise,
practical response: state whether the concern has merit, give a
recommendation, and note real trade-offs. Avoid giving definitive legal
advice — frame it as drafting/analysis input for the Managing Committee,
not formal legal advice. Keep the tone plain and direct, not
legalistic.

You will also be given zero or more EXISTING register entries that already
cover the same clause number(s) as the new comment. Decide whether the new
comment is raising a genuinely new concern (action "new") or is substantially
the same underlying concern as one of the existing entries — same clause,
same complaint — just from a different owner or worded differently (action
"merge"). When merging, "response" should be ONLY the short addendum to
append (e.g. a new angle this owner raised, or simply note agreement) — do
NOT rewrite the existing entry's response.

Respond with ONLY a single JSON object, no markdown fences, no commentary:
{
  "action": "new" | "merge",
  "merge_into_id": <int or null>,
  "category": "<short category label>",
  "status": "fix" | "flagged",
  "response": "<drafted response, or addendum text if action is merge>"
}
"""


def _client():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set in .env.")
    return Anthropic(api_key=api_key)


def find_candidates(entries, clause_ref_field):
    """Existing data.json entries that reference at least one of the same
    clause numbers as the new row's 'Section of the By laws' field."""
    new_refs = set(docx_clauses.extract_refs(clause_ref_field))
    if not new_refs:
        return []
    candidates = []
    for entry in entries:
        existing_refs = set(docx_clauses.extract_refs(entry.get("clause", "")))
        if new_refs & existing_refs:
            candidates.append(entry)
    return candidates


def _extract_json(text):
    text = text.strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in model response: {text!r}")
    return json.loads(match.group(0))


def draft(row, clause_text, candidates):
    """Call Claude to decide new-vs-merge and draft category/status/response."""
    model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")

    candidates_json = json.dumps(
        [
            {
                "id": c["id"],
                "clause": c.get("clause"),
                "category": c.get("category"),
                "raisedBy": c.get("raisedBy"),
                "query": c.get("query"),
                "response": c.get("response"),
            }
            for c in candidates
        ],
        indent=2,
        ensure_ascii=False,
    )

    user_message = f"""Owner comment to review:

Owner: {row['name']} ({row['unit_no']})
Clause reference given by owner: {row['clause_ref']}
Comment: {row['comment']}

Relevant bye-laws clause text:
{clause_text or '(no matching clause text found in the bye-laws document)'}

Existing register entries for the same clause(s) (empty list means none):
{candidates_json}
"""

    client = _client()
    resp = client.messages.create(
        model=model,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    text = "".join(block.text for block in resp.content if block.type == "text")
    return _extract_json(text)
