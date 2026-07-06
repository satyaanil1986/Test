#!/usr/bin/env python3
import json
import os
import sys

from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))

from lib import docx_clauses, drafter, render, sheets, state as state_mod

BASE_DIR = os.path.dirname(__file__)
DATA_PATH = os.path.join(BASE_DIR, "data.json")


def load_data():
    if not os.path.exists(DATA_PATH):
        return []
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(entries):
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
        f.write("\n")


def next_id(entries):
    return max((e["id"] for e in entries), default=0) + 1


def main():
    load_dotenv(os.path.join(BASE_DIR, ".env"))

    bylaws_path = os.environ.get("BYLAWS_DOCX_PATH", os.path.join(BASE_DIR, "bylaws.docx"))
    if not os.path.exists(bylaws_path):
        print(f"ERROR: bye-laws document not found at {bylaws_path}. "
              f"Set BYLAWS_DOCX_PATH in .env or place the file there.")
        sys.exit(1)

    entries = load_data()
    state = state_mod.load_state()

    print("Fetching sheet rows...")
    rows = sheets.fetch_rows()

    new_rows = [r for r in rows if state_mod.row_hash(r) not in state]
    print(f"{len(rows)} total rows, {len(new_rows)} new.")

    if not new_rows:
        render.render(entries)
        print("No new rows. Register regenerated from existing data.json (no content changes).")
        return

    clauses = docx_clauses.parse_clauses(bylaws_path)

    merged_count = 0
    created_count = 0

    for row in new_rows:
        h = state_mod.row_hash(row)
        clause_text = docx_clauses.gather_clause_text(clauses, row["clause_ref"])
        candidates = drafter.find_candidates(entries, row["clause_ref"])

        try:
            decision = drafter.draft(row, clause_text, candidates)
        except Exception as e:
            print(f"  ! Skipping row from {row['name']} ({row['timestamp']}): drafting failed: {e}")
            continue

        owner_label = f"{row['name']} ({row['unit_no']})" if row["unit_no"] else row["name"]

        if decision.get("action") == "merge" and decision.get("merge_into_id") is not None:
            target_id = decision["merge_into_id"]
            target = next((e for e in entries if e["id"] == target_id), None)
            if target is None:
                print(f"  ! merge_into_id {target_id} not found, creating new entry instead.")
                decision["action"] = "new"
            else:
                if owner_label not in target["raisedBy"]:
                    target["raisedBy"].append(owner_label)
                addendum = decision.get("response", "").strip()
                if addendum:
                    target["response"] = target["response"].rstrip() + f"\n\nAdditional input from {owner_label}: {addendum}"
                merged_count += 1
                state[h] = {"entryId": target_id, "action": "merge"}
                print(f"  merged into #{target_id}: {row['name']} on clause {row['clause_ref']}")

        if decision.get("action") != "merge":
            new_id = next_id(entries)
            entries.append({
                "id": new_id,
                "clause": row["clause_ref"],
                "category": decision.get("category", ""),
                "raisedBy": [owner_label],
                "status": decision.get("status", "flagged"),
                "query": row["comment"],
                "response": decision.get("response", ""),
            })
            created_count += 1
            state[h] = {"entryId": new_id, "action": "new"}
            print(f"  created #{new_id}: {row['name']} on clause {row['clause_ref']}")

    entries.sort(key=lambda e: e["id"])
    save_data(entries)
    state_mod.save_state(state)
    output_path = render.render(entries)

    print()
    print("--- Sync summary ---")
    print(f"New rows found:     {len(new_rows)}")
    print(f"Merged into existing entries: {merged_count}")
    print(f"New entries created:          {created_count}")
    print(f"Register regenerated at: {output_path}")
    print("Commit and push data.json, state.json and output/index.html to publish "
          "the update (GitHub Pages deploys automatically on push).")


if __name__ == "__main__":
    main()
