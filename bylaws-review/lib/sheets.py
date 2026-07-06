import json
import os

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

EXPECTED_HEADERS = [
    "Timestamp",
    "Email address",
    "Unit No",
    "Name",
    "Section of the By laws",
    "Comment/clarification point",
]


def _load_credentials():
    raw_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    key_file = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE")

    if raw_json:
        info = json.loads(raw_json)
        return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    if key_file:
        return service_account.Credentials.from_service_account_file(key_file, scopes=SCOPES)

    raise RuntimeError(
        "No Google credentials found. Set GOOGLE_SERVICE_ACCOUNT_JSON (key content) "
        "or GOOGLE_SERVICE_ACCOUNT_FILE (path to key file) in .env."
    )


def fetch_rows():
    """Return sheet rows as a list of dicts keyed by the sheet's own header row."""
    spreadsheet_id = os.environ.get("SPREADSHEET_ID")
    sheet_range = os.environ.get("SHEET_RANGE", "A:F")
    if not spreadsheet_id:
        raise RuntimeError("SPREADSHEET_ID is not set in .env.")

    creds = _load_credentials()
    service = build("sheets", "v4", credentials=creds)
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=sheet_range)
        .execute()
    )
    values = result.get("values", [])
    if not values:
        return []

    header = [h.strip() for h in values[0]]
    rows = []
    for raw in values[1:]:
        padded = raw + [""] * (len(header) - len(raw))
        row = dict(zip(header, padded))
        # normalize to the fixed keys the rest of the pipeline expects, tolerating
        # minor header wording drift in the form.
        rows.append(
            {
                "timestamp": row.get("Timestamp", "").strip(),
                "email": row.get("Email address", "").strip(),
                "unit_no": row.get("Unit No", "").strip(),
                "name": row.get("Name", "").strip(),
                "clause_ref": row.get("Section of the By laws", "").strip(),
                "comment": row.get("Comment/clarification point", "").strip(),
            }
        )
    return [r for r in rows if r["comment"]]
