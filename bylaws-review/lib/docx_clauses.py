import re

from docx import Document

# Top-level clause headings use Word's "Heading 2" style with literal text like
# "7. Quorum" or "28. Maintenance Charges, Sinking Fund, and Special Assessments".
TOP_HEADING_RE = re.compile(r"^(\d+)\.?\s*(.*)$")
TOP_HEADING_STYLE = "Heading 2"
SKIP_STYLE_PREFIX = "Heading 1"

# Matches individual clause references inside a free-text "Section of the By laws" cell,
# e.g. "7.1 / 7.3", "7.1, 28.4", "Clause 7.1"
CLAUSE_REF_RE = re.compile(r"\d+(?:\.\d+)+|\b\d+\b")


def _numbering(paragraph):
    """Return (numId, ilvl) if this paragraph is part of a Word auto-numbered
    list, else (None, None). Sub-clauses like '7.1', '28.4' aren't typed as
    literal text in this document -- they're rendered by Word's own list
    numbering, so we have to read it from the paragraph's numPr instead."""
    pPr = paragraph._p.pPr
    numPr = pPr.numPr if pPr is not None else None
    if numPr is None or numPr.numId is None:
        return None, None
    ilvl = numPr.ilvl.val if numPr.ilvl is not None else None
    return numPr.numId.val, ilvl


def parse_clauses(docx_path):
    """Return {clause_number: text}, e.g. '28' -> heading line, '28.4' -> that
    sub-clause's body text.

    Each Heading-2 paragraph ("28. Maintenance...") opens a new top-level
    clause. Within it, the *first* numbered-list id encountered is treated as
    that section's primary enumeration -- each new item on that same list is
    the next sub-clause (28.1, 28.2, ...). Paragraphs on any other list (the
    document reuses a handful of numIds as generic lettered/roman sub-bullets
    throughout, e.g. "(a)/(b)" under a single numbered point) or with no
    numbering at all are treated as continuation text of the current
    sub-clause, since they aren't independently citable clause numbers.
    """
    doc = Document(docx_path)
    clauses = {}
    top_order = []
    children_by_top = {}

    current_top = None
    primary_numid = None
    sub_counter = 0
    current_sub_number = None
    current_sub_lines = []

    def flush_sub():
        if current_sub_number is not None:
            text = "\n".join(l for l in current_sub_lines if l.strip()).strip()
            clauses[current_sub_number] = text
            children_by_top[current_top].append((current_sub_number, text))

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        if para.style.name == TOP_HEADING_STYLE:
            flush_sub()
            m = TOP_HEADING_RE.match(text)
            if not m:
                current_top = None
                continue
            current_top = m.group(1)
            top_order.append((current_top, text))
            children_by_top[current_top] = []
            clauses[current_top] = text
            primary_numid = None
            sub_counter = 0
            current_sub_number = None
            current_sub_lines = []
            continue

        if para.style.name.startswith(SKIP_STYLE_PREFIX):
            continue  # chapter title, TOC heading, etc: not clause content

        if current_top is None:
            continue  # preamble / front matter before the first numbered clause

        num_id, _ilvl = _numbering(para)
        if num_id is not None:
            if primary_numid is None:
                primary_numid = num_id
            if num_id == primary_numid:
                flush_sub()
                sub_counter += 1
                current_sub_number = f"{current_top}.{sub_counter}"
                current_sub_lines = [text]
                continue

        # continuation text: either unnumbered, or on a shared/generic
        # sub-bullet list -- fold it into whichever clause is currently open.
        if current_sub_number is not None:
            current_sub_lines.append(text)
        else:
            clauses[current_top] = clauses[current_top] + "\n" + text

    flush_sub()

    # Give each top-level number a richer fallback: heading + all its
    # sub-clauses, for when an owner cites only the parent clause (e.g. "28").
    for top, heading_text in top_order:
        children = children_by_top.get(top, [])
        if children:
            body = "\n".join(f"{num}: {t}" for num, t in children)
            clauses[top] = f"{heading_text}\n{body}"

    return clauses


def extract_refs(clause_ref_field):
    """Pull out individual clause numbers like '7.1' from a free-text field
    such as '7.1 / 7.3' or 'Clause 28.4'."""
    return CLAUSE_REF_RE.findall(clause_ref_field or "")


def lookup_clause_text(clauses, ref):
    """Look up a single clause number, falling back to its parent clause
    (e.g. '7.1' -> '7') if the exact sub-clause wasn't parsed as its own heading."""
    if ref in clauses:
        return clauses[ref]
    if "." in ref:
        parent = ref.rsplit(".", 1)[0]
        if parent in clauses:
            return clauses[parent]
    return None


def gather_clause_text(clauses, clause_ref_field):
    """Given the raw 'Section of the By laws' field, return a combined block of
    clause text for every referenced clause found, e.g. '7.1 / 7.3'."""
    refs = extract_refs(clause_ref_field)
    parts = []
    for ref in refs:
        text = lookup_clause_text(clauses, ref)
        if text:
            parts.append(f"[Clause {ref}]\n{text}")
        else:
            parts.append(f"[Clause {ref}]\n(clause text not found in bye-laws document)")
    return "\n\n".join(parts)
