# Contributing

Thanks for improving Context Image Harvester.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
python -m pip install -e '.[dev]'
```

Run checks before opening a pull request:

```bash
ruff check .
pytest
```

## Pull requests

- Create a branch; do not push feature work directly to `main`.
- Keep API keys and harvested image packs out of commits.
- Add or update tests for behavior changes.
- Provider changes must preserve quotas, rate limits, provenance fields, and graceful failure.
- Security changes involving URL fetching should include tests for private-network/redirect handling.

## Adding a provider

Implement `Provider.search()` in `src/context_image_harvester/providers/`, return normalized `Candidate` objects, and add parser/cache/error tests. Keep provider-specific authentication in environment variables or GitHub secrets.
