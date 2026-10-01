## 1.1.0

### Added
- Backward-compatible structured item context with `context`, `must_include`, and `must_avoid`.
- Adaptive second SerpApi query only when the first query still leaves an item short.
- Optional OpenCLIP real-photo likelihood scoring alongside semantic relevance.

### Changed
- Paid-search usage is persisted before each uncached SerpApi request for crash-safe quota enforcement.
- Selected source URLs are persisted across resume chains.
- Download workers use thread-local HTTP sessions and no longer mutate Pillow's process-global pixel limit.
- Quota estimates account for up to two adaptive paid query variants per provider.

