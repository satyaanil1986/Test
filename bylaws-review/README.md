# Bye-Laws Review Register

Keeps `data.json` (the review register) in sync with the Google Form
response sheet, drafts category/response text via Claude for new comments,
and regenerates `output/index.html`, which GitHub Pages serves automatically
on every push.

## One-time setup

### 1. Google Cloud service account (for reading the Sheet)

1. Go to https://console.cloud.google.com/ and create a new project (or reuse
   one you have).
2. In "APIs & Services > Library", enable the **Google Sheets API**.
3. In "APIs & Services > Credentials", click **Create credentials > Service
   account**. Give it any name (e.g. `bylaws-sync`). No roles needed.
4. Open the service account, go to the **Keys** tab, **Add key > Create new
   key > JSON**. This downloads a JSON file — that's your credential.
5. Open the response Sheet
   (https://docs.google.com/spreadsheets/d/1P2IG4yRPfUq7VVsfUMF_Vg0TzY3kspVg16JSqTmYpkA/edit),
   click **Share**, and add the service account's email address (looks like
   `bylaws-sync@your-project.iam.gserviceaccount.com`, visible on the service
   account's page) with **Viewer** access.
6. Paste the full contents of the downloaded JSON file into `.env` as
   `GOOGLE_SERVICE_ACCOUNT_JSON` (one line), or save the file somewhere and
   point `GOOGLE_SERVICE_ACCOUNT_FILE` at its path instead.

### 2. Anthropic API key

1. Go to https://console.anthropic.com/ (create an account if needed), open
   **API Keys**, and create a new key.
2. Put it in `.env` as `ANTHROPIC_API_KEY`.

### 3. Local files this tool needs

- Copy `.env.example` to `.env` and fill in the values from steps 1-2.
- Put the Bye-Laws Word document at `bylaws-review/bylaws.docx` (or set
  `BYLAWS_DOCX_PATH` in `.env` to wherever it lives). This file is committed
  to the repo (not gitignored) so it survives between sessions in an
  ephemeral container — if you'd rather it not be committed, say so and this
  can be reworked to expect a re-upload each run instead.
- Paste your seed dataset into `bylaws-review/data.json` (replacing the `[]`
  placeholder) — it should already be in the right shape.

### 4. Enable GitHub Pages (one-time, manual)

This repo includes `.github/workflows/bylaws-pages.yml`, which builds and
deploys `bylaws-review/output/index.html` on every push. GitHub Pages itself
still needs to be turned on once:

Repo **Settings > Pages > Build and deployment > Source**, select **GitHub
Actions**. After that, every push that changes `bylaws-review/output/**`
re-deploys automatically — no manual publish step.

### 5. Install Python dependencies

```
cd bylaws-review
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Running a sync

```
cd bylaws-review
python sync.py
```

This will:
1. Read all rows from the Google Form response sheet.
2. Skip rows already processed (tracked in `state.json` by a hash of
   Timestamp + Email + Comment).
3. For each new row, look up the referenced clause(s) in the bye-laws
   document, check `data.json` for an existing entry on the same clause, and
   ask Claude to either draft a new register entry or write an addendum to
   merge into the existing one.
4. Update `data.json` and `state.json`, and regenerate
   `output/index.html`.
5. Print a summary: rows found, merged vs. newly created, output path.

**After it runs**, commit and push `data.json`, `state.json` and
`output/index.html` — that push is what triggers the Pages deployment.

## Notes on manual edits

Sync only ever *appends* an addendum paragraph to an existing entry's
`response` when a new comment merges into it — it never regenerates or
overwrites the full text of an entry you've hand-edited. Entries with no new
matching comments are left completely untouched by a sync run, so feel free
to tweak `category`/`response`/`status` by hand in `data.json` between
syncs.
