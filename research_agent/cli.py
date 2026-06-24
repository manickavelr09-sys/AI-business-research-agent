from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from research_agent.orchestrator import ResearchAgent


async def _run(args: argparse.Namespace) -> int:
    agent = ResearchAgent()
    final_report = None
    try:
        async for event in agent.research_stream(args.query, limit=args.limit):
            if event["event"] == "business_discovered" and args.stream:
                print(json.dumps(event["business"], ensure_ascii=False))
            elif event["event"] == "completed":
                final_report = event["report"]
    finally:
        await agent.close()

    if final_report is None:
        raise RuntimeError("Research did not complete")
    payload = json.dumps(final_report, indent=2, ensure_ascii=False)
    if args.json_out:
        Path(args.json_out).write_text(payload, encoding="utf-8")
    print(payload)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AI Business Research Agent")
    parser.add_argument("query", help='Example: "Cardiologists in Birmingham"')
    parser.add_argument("--limit", type=int, default=None, help="Maximum candidate URLs to process")
    parser.add_argument("--json-out", default="", help="Write final report JSON to this path")
    parser.add_argument("--stream", action="store_true", help="Print each discovered business as NDJSON")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
