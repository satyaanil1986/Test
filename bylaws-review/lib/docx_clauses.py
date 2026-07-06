import re

from docx import Document

# Matches a clause heading at the start of a paragraph, e.g. "7.1", "7.1.", "28.4 Quorum"
CLAUSE_HEADING_RE = re.compile(r"^(\d+(?:\.\d+)*)\.?\s*(.*)$")

# Matches individual clause references inside a free-text "Section of the By laws" cell,
# e.g. "7.1 / 7.3", "7.1, 28.4", "Clause 7.1"
CLAUSE_REF_RE = re.compile(r"\d+(?:\.\d+)+|\b\d+\b")


def parse_clauses(docx_path):
    """Return {clause_number: full_text} by walking paragraphs and treating any
    paragraph that starts with a numeric clause pattern as the start of a new clause."""
    doc = Document(docx_path)
    clauses = {}
    current_number = None
    current_lines = []

    def flush():
        if current_number is not None:
            text = "\n".join(l for l in current_lines if l.strip())
            clauses[current_number] = text.strip()

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        m = CLAUSE_HEADING_RE.match(text)
        if m:
            flush()
            current_number = m.group(1)
            current_lines = [text]
        else:
            if current_number is not None:
                current_lines.append(text)

    flush()
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
