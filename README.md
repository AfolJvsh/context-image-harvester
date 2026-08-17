# Context Image Harvester

A general-purpose Python tool for building **prompt-aligned, globally unique real-photo review packs** from Pexels, Google Images and Bing Images through SerpApi, and Wikimedia Commons.

The project is designed for websites, product catalogs, service pages, editorial planning, research collections, and other workflows where many topics need several candidate photographs without repeatedly selecting the same or near-identical image.

> **Rights notice:** this is a discovery and review tool, not a copyright-clearance system. Pexels and Wikimedia expose useful provenance/license information. Arbitrary web results discovered through SerpApi must be reviewed at their source before publication.

## Highlights

- Quota-aware order: **Pexels → Google only if needed → Wikimedia only if needed → Bing only if needed**.
- Exact SHA-256 and global perceptual pHash duplicate rejection.
- Bounded parallel image downloads; provider search requests stay controlled and sequential.
- Search caching and resumable runs, including a persisted SerpApi request budget.
- SSRF/private-network URL blocking and redirect validation for arbitrary web downloads.
- Download byte caps, MIME checks, minimum dimensions, maximum pixel count, and Pillow decompression-bomb protection.
- Structured rejection reasons and provider/cache metrics in `summary.json`.
- `review` and `strict` rights modes.
- Optional OpenCLIP semantic ranking.
- Metadata, resolution, provider-trust, and visual-diversity scoring.
- Separate `search_queries` and semantic `prompt` fields.
- Interactive offline contact sheet with approve/reject state, filters, and `approved.json` / `rejected.json` export.
- Installable CLI, Dockerfile, tests, CI, CodeQL, Dependabot, and release automation.

## Installation

Python 3.11+ is required; Python 3.12 is recommended.

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
python -m pip install .
```

For development:

```bash
python -m pip install -e '.[dev]'
```

For optional CLIP semantic ranking:

```bash
python -m pip install -e '.[clip]'
```

## API keys

Copy `.env.example` for reference, then set values in your shell or environment manager:

```text
PEXELS_API_KEY
SERPAPI_API_KEY
SERPAPI_MAX_SEARCHES
WIKIMEDIA_USER_AGENT
```

You may run with only a subset of providers, but fewer providers can leave prompts short. Never commit real keys.

For GitHub Actions, add `PEXELS_API_KEY` and `SERPAPI_API_KEY` under **Settings → Secrets and variables → Actions**.

## Prompt format

```json
[
  {
    "id": 1,
    "name": "Laptop Repair",
    "prompt": "real professional photograph of a technician repairing a laptop on a clean electronics workbench",
    "search_queries": [
      "laptop repair technician workbench",
      "computer repair technician laptop"
    ]
  }
]
```

`prompt` describes semantic intent and is used by relevance scoring/CLIP. `search_queries` contains concise search-engine wording. If `search_queries` is omitted, the prompt is used.

Aliases are supported: `service`/`title` for `name`, and `search_query`/`query` for `prompt`. A simple list of strings is also accepted.

See [`examples/prompts.example.json`](examples/prompts.example.json).

## Estimate before spending quota

```bash
context-image-harvester estimate examples/prompts.example.json \
  --per-item 8 \
  --serpapi-max-searches 50
```

Or use `--dry-run` on the harvest command:

```bash
context-image-harvester harvest prompts.json --per-item 8 --dry-run
```

The estimate shows target image count, worst-case Google/Bing searches, and the configured hard paid-search ceiling. Actual usage can be lower because Pexels is attempted first and valid cached SerpApi results do not consume a new request in this tool.

## Harvest

```bash
context-image-harvester harvest examples/prompts.example.json \
  --per-item 8 \
  --output image_review_pack
```

The original entry point remains supported:

```bash
python image_harvester.py examples/prompts.example.json --per-item 8
```

### Useful options

```text
--per-item N                    final candidates per item (default 8)
--per-provider N                search candidates requested per provider (default 25)
--near-duplicate-hamming N      pHash duplicate threshold (default 8)
--serpapi-max-searches N        paid-search hard ceiling (default 110)
--max-download-mb N             candidate byte limit (default 25 MB)
--max-pixels N                  decoded-image pixel limit (default 50,000,000)
--download-workers N            concurrent image downloads (default 4)
--cache-dir PATH                search cache location
--cache-ttl-hours N             search cache lifetime (default 168)
--rights-mode review|strict     source-rights policy
--resume                        continue a prior output/state chain
--enable-clip                   enable optional OpenCLIP semantic scoring
--no-zip                        leave output directory without creating ZIP
--dry-run                       estimate only; perform no provider requests/downloads
```

## Provider strategy and quota behavior

For each item:

```text
Pexels
  │ enough valid/diverse candidates?
  ├─ yes → rank/select/save
  └─ no
       ▼
SerpApi Google Images
  │ enough?
  ├─ yes → rank/select/save
  └─ no
       ▼
Wikimedia Commons
  │ enough?
  ├─ yes → rank/select/save
  └─ no
       ▼
SerpApi Bing Images
```

In `strict` rights mode, SerpApi discovery providers are skipped completely, so paid searches are not spent on candidates that strict mode would reject.

The SerpApi counter is persisted in `state.json`, so resuming the same run does not reset the configured safety ceiling.

## Wikimedia behavior

Wikimedia is fallback-only. The client:

- identifies itself with `WIKIMEDIA_USER_AGENT`;
- uses serial API requests;
- waits between requests;
- sends `maxlag=5`;
- handles HTTP 429/503 and `Retry-After`;
- temporarily backs off rather than repeatedly hammering Commons.

## Safety model

Web-discovered image URLs are treated as untrusted input. The downloader rejects non-HTTP(S) schemes, localhost/private/link-local/reserved addresses, and unsafe redirect targets. It also applies byte, MIME, decoded-pixel, decompression, minimum-dimension, and redirect-count limits.

This is defense in depth, not a perfect network sandbox. For high-trust environments, run the tool in an isolated container or runner with network egress controls. See [`SECURITY.md`](SECURITY.md).

The output directory is recreated for non-resume runs and guards obvious dangerous paths such as `/`, the current directory, and the user's home directory. Always use a dedicated output folder.

## Duplicate detection

The tool performs global duplicate checks across the run:

1. **SHA-256** for byte-identical files.
2. **Perceptual pHash** for visually near-identical resized/recompressed variants.

The pHash implementation is built into the project. Increase `--near-duplicate-hamming` to reject more visual similarity; decrease it if the filter is too aggressive.

## Relevance and diversity ranking

Every prepared candidate receives:

- metadata relevance score;
- resolution score;
- provider-trust score;
- semantic score (metadata fallback, or OpenCLIP when enabled);
- visual-diversity contribution during greedy selection.

CLIP is optional because its Torch/OpenCLIP dependencies are much larger than the default installation.

## Rights modes

### `review` (default)

Uses all configured providers. SerpApi-discovered web results receive `rights_status: manual-review` and must be checked at the source.

### `strict`

Only accepts candidates from providers/results carrying verified provider or license metadata. Google/Bing discovery is skipped to avoid wasting quota.

Rights status, license metadata, and `requires_manual_review` are written to the manifest.

## Cache and resume

Search responses are cached under `.cache/context-image-harvester` by default. Cached provider responses make reruns faster and can avoid fresh paid searches.

Use:

```bash
context-image-harvester harvest prompts.json --output image_review_pack --resume
```

`state.json` tracks records, selected hashes, completed item IDs, and paid-search count. If a previous item was incomplete, resume removes that partial item cleanly and retries it rather than duplicating its existing candidates.

## Output

```text
image_review_pack/
├── images/
├── source_originals/
├── CONTACT_SHEET.html
├── DESCRIPTIONS.md
├── manifest.csv
├── manifest.json
├── summary.json
└── state.json              # resume bookkeeping; excluded from ZIP

image_review_pack.zip
```

`source_originals/` contains normalized/resized source copies used for review; they are not literal untouched originals and are not proof of usage rights.

`summary.json` includes completion counts, paid-search usage, provider searches, cache hits, total downloads, and structured rejection reasons such as `unsafe_url`, `too_large`, `bad_mime`, `phash_global_duplicate`, or `rights_not_verified`.

## Interactive review

Open `CONTACT_SHEET.html` locally. Each candidate can be marked **Approve** or **Reject**. Review state is stored in browser `localStorage`, and the page can export `approved.json` or `rejected.json`. Filters are available for provider, rights status, and review status.

## GitHub Actions

### CI

`.github/workflows/ci.yml` runs on pull requests and `main` pushes across supported Python versions. It installs the development extra, runs Ruff, pytest, and a CLI estimate smoke test. It does **not** consume provider API quota.

### Manual harvest

`.github/workflows/harvest.yml` is manual-dispatch only. Choose the prompt file, target count, SerpApi ceiling, rights mode, and optional CLIP ranking. The workflow uploads **only the final ZIP**, avoiding a duplicate folder-plus-ZIP artifact.

### Security and maintenance

- CodeQL scans Python on PRs, `main`, and weekly.
- Dependabot checks Python and GitHub Actions dependencies weekly.
- Tagging `v*` builds the package and creates a GitHub release containing the distribution files.

## Docker

```bash
docker build -t context-image-harvester .
docker run --rm \
  -e PEXELS_API_KEY \
  -e SERPAPI_API_KEY \
  -v "$PWD:/work" \
  -w /work \
  context-image-harvester harvest prompts.json --output image_review_pack
```

## Development

```bash
python -m pip install -e '.[dev]'
ruff check .
pytest
```

See [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`docs/architecture.md`](docs/architecture.md).

## Protecting `main`

Recommended ruleset:

- target `main`;
- restrict deletions;
- block force pushes;
- require a pull request before merging;
- require at least one approval;
- dismiss stale approvals;
- require conversation resolution;
- require CI checks before merging.

## License

The software is MIT licensed. Harvested/discovered images retain their own source licenses and rights; the repository's MIT license does not cover those image assets.
