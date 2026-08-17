# Architecture

```text
Prompt JSON
   │
   ▼
CLI / config
   │
   ▼
Harvester orchestrator
   │
   ├── Pexels provider
   ├── SerpApi Google provider
   ├── Wikimedia provider
   └── SerpApi Bing provider
           │
           ▼
      Search cache
           │
           ▼
Candidate downloader
  - public-network guard
  - redirect checks
  - streaming byte cap
  - MIME/pixel/decompression checks
           │
           ▼
Hash + validation
  - SHA-256
  - pHash
  - rights-mode filter
           │
           ▼
Ranking / selection
  - metadata relevance
  - resolution
  - provider trust
  - optional CLIP
  - visual diversity
           │
           ▼
Run state / resume
           │
           ▼
Reports + interactive review + ZIP
```

Provider API requests remain sequential and provider-aware. Candidate image downloads use a bounded worker pool. Search results are cached outside the output directory by default so a new output pack can reuse prior searches without consuming fresh paid requests when cache entries are valid.

`state.json` is intentionally excluded from the final ZIP. It stores resume bookkeeping, selected hashes, completed item IDs, and the persisted paid-search count for the active run chain.
