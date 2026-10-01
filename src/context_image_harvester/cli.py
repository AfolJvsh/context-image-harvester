from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

from .config import HarvesterConfig
from .harvester import Harvester
from .utils import load_items


def _positive(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def estimate(
    items_count: int,
    per_item: int,
    serpapi_cap: int,
    rights_mode: str = "review",
    paid_query_count: int | None = None,
) -> dict:
    query_count = items_count if paid_query_count is None else max(0, paid_query_count)
    google_max = 0 if rights_mode == "strict" else query_count
    bing_max = 0 if rights_mode == "strict" else query_count
    return {
        "items": items_count,
        "target_images": items_count * per_item,
        "max_google_searches": google_max,
        "max_bing_searches": bing_max,
        "worst_case_serpapi_without_cap": google_max + bing_max,
        "configured_serpapi_cap": serpapi_cap,
        "maximum_paid_searches_this_run": min(serpapi_cap, google_max + bing_max),
        "rights_mode": rights_mode,
        "note": (
            "Actual usage can be lower because Pexels is attempted first, "
            "SerpApi query variants are adaptive, and cached searches consume no new request."
        ),
    }


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("prompts", type=Path, help="JSON prompt file")
    parser.add_argument("--per-item", type=_positive, default=8)
    parser.add_argument(
        "--serpapi-max-searches",
        type=int,
        default=int(os.getenv("SERPAPI_MAX_SEARCHES", "110")),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="context-image-harvester")
    sub = parser.add_subparsers(dest="command", required=True)

    harvest = sub.add_parser("harvest", help="Harvest and rank image candidates")
    _add_common(harvest)
    harvest.add_argument("--output", type=Path, default=Path("image_review_pack"))
    harvest.add_argument("--per-provider", type=_positive, default=25)
    harvest.add_argument("--near-duplicate-hamming", type=int, default=8)
    harvest.add_argument("--max-download-mb", type=_positive, default=25)
    harvest.add_argument("--max-pixels", type=_positive, default=50_000_000)
    harvest.add_argument("--timeout", type=_positive, default=35)
    harvest.add_argument("--download-workers", type=_positive, default=4)
    harvest.add_argument(
        "--cache-dir",
        type=Path,
        default=Path(".cache/context-image-harvester"),
    )
    harvest.add_argument("--cache-ttl-hours", type=int, default=168)
    harvest.add_argument(
        "--rights-mode",
        choices=["review", "strict"],
        default="review",
    )
    harvest.add_argument("--resume", action="store_true")
    harvest.add_argument("--dry-run", action="store_true")
    harvest.add_argument("--no-zip", action="store_true")
    harvest.add_argument("--enable-clip", action="store_true")
    harvest.add_argument("--clip-model", default="ViT-B-32")
    harvest.add_argument("--clip-pretrained", default="laion2b_s34b_b79k")
    harvest.add_argument(
        "--keep-existing-output",
        action="store_true",
        help="Refuse to overwrite an existing output directory (legacy compatibility).",
    )

    estimate_parser = sub.add_parser(
        "estimate",
        help="Estimate target size and maximum SerpApi usage",
    )
    _add_common(estimate_parser)
    estimate_parser.add_argument(
        "--rights-mode",
        choices=["review", "strict"],
        default="review",
    )
    return parser


def _safe_output(path: Path) -> Path:
    output = path.resolve()
    cwd = Path.cwd().resolve()
    home = Path.home().resolve()
    dangerous = {Path("/").resolve(), cwd, home, home.parent.resolve()}
    if os.name == "nt" and output.anchor:
        dangerous.add(Path(output.anchor).resolve())
    if output in dangerous:
        raise ValueError(f"Refusing dangerous output path: {output}")
    return output


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] not in {"harvest", "estimate", "-h", "--help"}:
        argv.insert(0, "harvest")
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        items = load_items(args.prompts)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))

    paid_query_count = sum(
        min(2, max(1, len(item.search_queries)))
        for item in items
    )
    usage = estimate(
        len(items),
        args.per_item,
        max(0, args.serpapi_max_searches),
        getattr(args, "rights_mode", "review"),
        paid_query_count=paid_query_count,
    )
    if args.command == "estimate" or getattr(args, "dry_run", False):
        print(json.dumps(usage, indent=2))
        return 0

    try:
        output = _safe_output(args.output)
    except ValueError as exc:
        parser.error(str(exc))

    if output.exists() and not args.resume:
        if args.keep_existing_output:
            parser.error(f"Output already exists: {output}")
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)

    config = HarvesterConfig(
        output=output,
        per_item=args.per_item,
        per_provider=args.per_provider,
        phash_distance=max(0, args.near_duplicate_hamming),
        serpapi_max=max(0, args.serpapi_max_searches),
        max_download_mb=args.max_download_mb,
        timeout=args.timeout,
        max_pixels=args.max_pixels,
        download_workers=args.download_workers,
        rights_mode=args.rights_mode,
        cache_dir=args.cache_dir.resolve(),
        cache_ttl_hours=max(0, args.cache_ttl_hours),
        resume=args.resume,
        enable_clip=args.enable_clip,
        clip_model=args.clip_model,
        clip_pretrained=args.clip_pretrained,
    )
    try:
        summary, zip_path = Harvester(config).run(
            items,
            create_zip=not args.no_zip,
        )
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(summary, indent=2))
    if zip_path:
        print(f"ZIP: {zip_path}")
    return 0 if summary["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
