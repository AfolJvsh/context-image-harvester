# Changelog

All notable changes to this project are documented here. The project follows Semantic Versioning.


## 1.1.0 - 2026-10-01

### Added
- Backward-compatible structured item context with `context`, `must_include`, and `must_avoid`.
- Adaptive second SerpApi query only when the first query still leaves an item short.
- Optional OpenCLIP real-photo likelihood scoring alongside semantic relevance.

### Changed
- Paid-search usage is persisted before each uncached SerpApi request for crash-safe quota enforcement.
- Selected source URLs are persisted across resume chains.
- Download workers use thread-local HTTP sessions and no longer mutate Pillow's process-global pixel limit.
- Quota estimates account for up to two adaptive paid query variants per provider.

## 1.0.0 - 2026-08-17

### Added
- Installable `context-image-harvester` CLI with backward-compatible `image_harvester.py` entry point.
- Provider modules for Pexels, SerpApi Google Images, Wikimedia Commons, and SerpApi Bing Images.
- Pexels-first quota-aware provider ordering so paid search is only used when needed.
- Dry-run / `estimate` command for target and SerpApi budget planning.
- SSRF/private-network URL guard with redirect validation for arbitrary image downloads.
- Streaming downloads with byte, MIME, pixel, and decompression-bomb limits.
- Structured rejection metrics in `summary.json`.
- Built-in SHA-256 and perceptual pHash duplicate protection without ImageHash dependency.
- Search-result cache with TTL and resumable run state.
- Persisted SerpApi budget across resumed runs.
- Bounded parallel candidate downloads while provider API searches stay sequential.
- `review` and `strict` rights modes.
- Optional OpenCLIP semantic ranking via the `clip` extra.
- Metadata, resolution, provider-trust, semantic, and visual-diversity scoring.
- Per-item `search_queries` separate from the semantic prompt.
- Interactive offline contact sheet with approve/reject state, filters, and JSON export.
- Pytest test suite, Ruff CI, CodeQL, Dependabot, release workflow, Dockerfile, issue templates, PR template, contributing and security guides.

### Changed
- GitHub Actions uploads only the final review ZIP to avoid duplicate artifact payloads.
- Wikimedia is fallback-only, throttled, and handles `Retry-After`/`maxlag`.
