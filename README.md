# Context Image Harvester

A general-purpose Python image harvester for building **prompt-aligned, globally unique real-photo review packs** from multiple online sources.

It was designed for workflows where you have many pages, products, services, topics, or content sections and want several candidate photographs for each one without reusing the same source image across the collection.

## What it does

The harvester searches multiple providers in a quota-conscious order:

1. **Pexels** — licensed stock-photo candidates.
2. **SerpApi Google Images** — broad web discovery.
3. **Wikimedia Commons** — provenance-friendly fallback, throttled to respect Wikimedia API limits.
4. **SerpApi Bing Images** — final backfill only when an item is still short.

For every downloaded candidate it can:

- reject metadata containing obvious AI-generation, illustration, vector, render, logo, or similar non-photo terms;
- reject images below the minimum practical dimensions;
- enforce a maximum download size;
- calculate an exact **SHA-256** hash;
- calculate a perceptual **pHash**;
- block exact duplicates globally;
- block perceptual near-duplicates globally;
- create a centered **16:10 review crop**;
- keep a resized source copy;
- write JSON and CSV manifests;
- create an HTML contact sheet;
- create a Markdown source/rights review file;
- package the run into a ZIP archive.

> **Important:** This is a discovery and review tool, not a copyright-clearance system. Pexels and Wikimedia provide useful license/provenance information. Images discovered through Google/Bing via SerpApi can come from arbitrary websites and must be rights-checked before publication.

## Requirements

- Python 3.11+ (3.12 recommended)
- Internet connection
- Optional but recommended:
  - Pexels API key
  - SerpApi API key

Install dependencies:

```bash
python -m venv .venv
```

macOS/Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## API keys

Never commit real API keys to the repository.

### Local usage

Set environment variables in your shell, or copy `.env.example` to `.env` and load the values through your preferred environment tooling.

Required variable names:

```text
PEXELS_API_KEY
SERPAPI_API_KEY
```

Optional controls:

```text
SERPAPI_MAX_SEARCHES
WIKIMEDIA_USER_AGENT
```

`WIKIMEDIA_USER_AGENT` should identify your application and provide a contact URL or email. The example points to the GitHub repository.

### GitHub Actions

In the repository, open:

**Settings → Secrets and variables → Actions → New repository secret**

Add:

```text
PEXELS_API_KEY
SERPAPI_API_KEY
```

The included workflow reads these values securely from GitHub Actions secrets.

## Prompt file format

The easiest format is a JSON array:

```json
[
  {
    "id": 1,
    "name": "Laptop Repair",
    "prompt": "real professional photograph of a technician repairing a laptop on a clean electronics workbench"
  },
  {
    "id": 2,
    "name": "Business WiFi",
    "prompt": "real professional photograph of a network technician installing a wireless access point in a modern office"
  }
]
```

The loader also understands the aliases:

- `service` or `title` instead of `name`
- `search_query` or `query` instead of `prompt`

A simple JSON list of strings is supported as well.

See [`examples/prompts.example.json`](examples/prompts.example.json).

## Local usage

Basic run:

```bash
python image_harvester.py examples/prompts.example.json
```

Keep 8 unique candidates per prompt:

```bash
python image_harvester.py examples/prompts.example.json \
  --per-item 8 \
  --output image_review_pack
```

Limit SerpApi usage:

```bash
python image_harvester.py examples/prompts.example.json \
  --per-item 8 \
  --serpapi-max-searches 50
```

More candidate discovery per provider:

```bash
python image_harvester.py prompts.json \
  --per-provider 40 \
  --per-item 10
```

Stricter near-duplicate rejection:

```bash
python image_harvester.py prompts.json \
  --near-duplicate-hamming 10
```

## CLI options

```text
prompts                       JSON prompt file
--output                      Output directory (default: image_review_pack)
--per-item                    Final candidates per prompt (default: 8)
--per-provider                Candidates requested from each provider (default: 25)
--near-duplicate-hamming      pHash Hamming distance treated as near-duplicate (default: 8)
--serpapi-max-searches        Hard SerpApi request ceiling (default: 110)
--max-download-mb             Reject downloads larger than this (default: 25 MB)
--timeout                     HTTP timeout in seconds (default: 35)
--keep-existing-output        Refuse to overwrite an existing output directory
```

## Provider strategy and SerpApi quota

The script intentionally does **not** query both SerpApi image engines for every prompt immediately.

For each prompt it performs:

```text
Pexels
   +
SerpApi Google Images (at most one search)
   ↓
Deduplicate / validate
   ↓
Enough candidates?
   ├─ yes → next prompt
   └─ no  → Wikimedia fallback
              ↓
            still short?
              └─ SerpApi Bing Images backfill
```

This makes a run much cheaper than blindly running two SerpApi searches for every item.

For example, 55 prompts that all fill from Pexels + Google use approximately **55 SerpApi searches**, not 440 searches.

The `--serpapi-max-searches` option is a hard safety ceiling.

## Wikimedia rate limiting

The Wikimedia client is deliberately conservative:

- Commons is only used as a fallback.
- API calls are serial.
- A minimum pause is applied between Commons API calls.
- `maxlag=5` is sent.
- HTTP `429` / `503` responses read `Retry-After` where available.
- A cooldown prevents repeated requests while Wikimedia is rate-limiting the client.
- The User-Agent identifies the application and includes contact information.

If Wikimedia is unavailable, the run can continue using the other providers.

## Output

A run creates a structure similar to:

```text
image_review_pack/
├── images/
│   ├── 001-laptop-repair-01.jpg
│   ├── 001-laptop-repair-02.jpg
│   └── ...
├── source_originals/
│   └── ...
├── CONTACT_SHEET.html
├── DESCRIPTIONS.md
├── manifest.csv
├── manifest.json
└── summary.json

image_review_pack.zip
```

### `images/`

Web/review-friendly centered 16:10 JPEG crops.

### `source_originals/`

Resized source copies used during validation. These are retained for review/reference, not as proof of usage rights.

### `manifest.json` / `manifest.csv`

Includes provider, title, source page, direct image URL, creator where available, license metadata, dimensions, SHA-256 and pHash.

### `CONTACT_SHEET.html`

Open it locally in a browser to review candidate images grouped by prompt.

### `summary.json`

Contains target counts, actual counts, per-item counts, SerpApi request usage, Wikimedia request count, and completion status.

## GitHub Actions

The repository includes `.github/workflows/harvest.yml`.

It is **manual-dispatch only** so pushing code does not accidentally consume API quota.

To run it:

1. Add the repository secrets described above.
2. Open **Actions → Image Harvest → Run workflow**.
3. Choose the prompt JSON path, candidates per item, and SerpApi cap.
4. Run the workflow.
5. Download the `image-review-pack` artifact when it completes.

## Safety notes

### Output-directory deletion

The script recreates its output directory at the beginning of a run. It includes guards against obvious dangerous paths such as `/`, your home directory, and the current repository directory.

Still, use a dedicated output name such as:

```text
image_review_pack
review_output
project_images
```

Do not intentionally point `--output` at folders containing unrelated data.

### Network and disk usage

A large job can download many candidates that are later rejected. Keep adequate disk space and bandwidth available.

The script rejects a candidate if its download exceeds `--max-download-mb` (25 MB by default).

## Duplicate detection

Two independent checks are used globally across the entire run:

1. **SHA-256** — catches byte-identical files.
2. **pHash** — catches visually similar versions such as resized/recompressed copies.

The default near-duplicate threshold is a pHash Hamming distance of `8`. Increase it to reject more visually similar images; decrease it if the filter is too aggressive.

## What this script does not do

- It does not prove that an image was made by a camera rather than AI.
- It does not provide legal clearance for arbitrary web images.
- It does not perform CLIP/embedding semantic ranking.
- It does not guarantee that every prompt reaches its requested candidate count.
- It does not bypass provider quotas or rate limits.

If a run finishes short, inspect `summary.json`, improve the prompt wording, increase `--per-provider`, add another licensed provider, or rerun after provider quota/rate limits reset.

## Protecting `main`

For a public repository, a sensible GitHub Ruleset is:

1. Open **Settings → Rules → Rulesets → New branch ruleset**.
2. Name it `Protect main`.
3. Set enforcement to **Active**.
4. Target the branch `main`.
5. Enable:
   - **Restrict deletions**
   - **Block force pushes**
   - **Require a pull request before merging**
   - **Require approvals**: `1`
   - **Dismiss stale pull request approvals when new commits are pushed**
   - **Require conversation resolution before merging**
6. Avoid adding bypass actors unless you intentionally want administrators to bypass the rules.
7. Save the ruleset.

This makes `main` PR-only and protects it from force-push/deletion.

## Contributing

Contributions are welcome. Please use a branch and open a pull request rather than pushing directly to `main`.

When changing provider integrations, preserve these principles:

- respect provider terms and rate limits;
- never commit API keys;
- keep global exact/perceptual duplicate protection;
- retain source URLs and rights metadata;
- fail safely when a provider becomes unavailable.

## License

The **software in this repository** is released under the MIT License. See [`LICENSE`](LICENSE).

Image files discovered or downloaded by the software are **not** covered by this repository's MIT License. Their individual source licenses/rights apply.
