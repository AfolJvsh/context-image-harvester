# Security Policy

## Supported version

Security fixes target the latest release line.

## Reporting a vulnerability

Please do not publish exploitable security details in a public issue. Use GitHub's private vulnerability reporting feature for this repository when available, or contact the repository owner privately through GitHub.

Useful reports include reproduction steps, affected version, impact, and a minimal proof of concept.

## Security boundaries

This tool downloads URLs discovered on the public web. It therefore includes best-effort SSRF/private-network blocking, redirect validation, byte limits, MIME checks, and image decompression limits. These controls reduce risk but should not be treated as a network sandbox. For high-trust environments, run the harvester in an isolated container/runner with restricted network access.

Never commit API keys. Use environment variables locally and repository secrets in GitHub Actions.
