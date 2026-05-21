import argparse
import asyncio
import json
import string
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import httpx


API_BASE = "https://www.googleapis.com/youtube/v3"
SEARCH_QUOTA_COST = 100
DEFAULT_MAX_PAGES = 1
DEFAULT_CONCURRENCY = 6
DEFAULT_QUOTA_BUDGET = 9_000
DEFAULT_QUERIES = list(string.ascii_lowercase) + list(string.digits)


class QuotaBudgetExceeded(RuntimeError):
    pass


class QuotaBudget:
    def __init__(self, units: int) -> None:
        self.remaining = units
        self._lock = asyncio.Lock()

    async def spend(self, units: int) -> None:
        async with self._lock:
            if self.remaining < units:
                raise QuotaBudgetExceeded(f"Quota budget exhausted. Remaining={self.remaining}, needed={units}")
            self.remaining -= units


@dataclass(frozen=True)
class ChannelRecord:
    title: str
    url: str
    published_at: str
    country_code: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crawl YouTube channel names and links by country and year."
    )
    parser.add_argument("--api-key", required=True, help="YouTube Data API key.")
    parser.add_argument("--output-dir", default="output", help="Base output directory. Default: output")
    parser.add_argument("--start-year", type=int, default=2005, help="Start year. Default: 2005")
    parser.add_argument(
        "--end-year",
        type=int,
        default=datetime.now(timezone.utc).year,
        help="End year. Default: current UTC year",
    )
    parser.add_argument("--countries", nargs="*", help="ISO-3166-1 alpha-2 country codes. Example: US VN JP")
    parser.add_argument(
        "--max-pages-per-query",
        type=int,
        default=DEFAULT_MAX_PAGES,
        help="Max API pages per query/year/country. Default: 1",
    )
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY, help="Async concurrency. Default: 6")
    parser.add_argument("--quota-budget", type=int, default=DEFAULT_QUOTA_BUDGET, help="Max quota units to spend. Default: 9000")
    parser.add_argument("--queries", nargs="*", help="Custom search seed queries. Default: a-z 0-9")
    parser.add_argument("--no-resume", action="store_true", help="Overwrite existing year files instead of skipping them")
    return parser.parse_args()


def year_range(start_year: int, end_year: int) -> Iterable[int]:
    if start_year > end_year:
        raise ValueError("start-year must be <= end-year")
    return range(start_year, end_year + 1)


def output_path(base_dir: Path, country_code: str, year: int) -> Path:
    return base_dir / country_code / f"{year}.txt"


async def fetch_json(client: httpx.AsyncClient, path: str, params: dict, budget: QuotaBudget | None = None) -> dict:
    if path == "/search" and budget:
        await budget.spend(SEARCH_QUOTA_COST)

    last_error: Exception | None = None
    for attempt in range(4):
        try:
            response = await client.get(f"{API_BASE}{path}", params=params, timeout=30.0)
            if response.status_code in {429, 500, 502, 503, 504}:
                await asyncio.sleep(2**attempt)
                continue
            response.raise_for_status()
            return response.json()
        except (httpx.TimeoutException, httpx.TransportError) as error:
            last_error = error
            await asyncio.sleep(2**attempt)

    if last_error:
        raise last_error
    response.raise_for_status()
    return response.json()


async def fetch_supported_regions(client: httpx.AsyncClient, api_key: str) -> list[str]:
    payload = await fetch_json(client, "/i18nRegions", {"part": "snippet", "hl": "en_US", "key": api_key})
    regions = sorted(
        {
            item["snippet"]["gl"]
            for item in payload.get("items", [])
            if item.get("snippet", {}).get("gl")
        }
    )
    if not regions:
        raise RuntimeError("No supported regions returned from YouTube API")
    return regions


async def search_channels(
    client: httpx.AsyncClient,
    api_key: str,
    country_code: str,
    year: int,
    query: str,
    max_pages: int,
    budget: QuotaBudget,
) -> list[ChannelRecord]:
    records: list[ChannelRecord] = []
    next_page_token = None
    published_after = f"{year}-01-01T00:00:00Z"
    published_before = f"{year + 1}-01-01T00:00:00Z"

    for _ in range(max_pages):
        params = {
            "part": "snippet",
            "type": "channel",
            "maxResults": 50,
            "q": query,
            "regionCode": country_code,
            "publishedAfter": published_after,
            "publishedBefore": published_before,
            "key": api_key,
        }
        if next_page_token:
            params["pageToken"] = next_page_token

        payload = await fetch_json(client, "/search", params, budget)
        for item in payload.get("items", []):
            snippet = item.get("snippet", {})
            channel_id = snippet.get("channelId") or item.get("id", {}).get("channelId")
            title = (snippet.get("channelTitle") or snippet.get("title") or "").strip()
            published_at = snippet.get("publishedAt", "")
            if not channel_id or not title:
                continue
            records.append(
                ChannelRecord(
                    title=title.replace("\n", " ").strip(),
                    url=f"https://www.youtube.com/channel/{channel_id}",
                    published_at=published_at,
                    country_code=country_code,
                )
            )

        next_page_token = payload.get("nextPageToken")
        if not next_page_token:
            break

    return records


async def collect_country_year(
    client: httpx.AsyncClient,
    api_key: str,
    country_code: str,
    year: int,
    queries: list[str],
    max_pages: int,
    semaphore: asyncio.Semaphore,
    budget: QuotaBudget,
) -> tuple[str, int, list[ChannelRecord]]:
    async def bounded_search(seed: str) -> list[ChannelRecord]:
        async with semaphore:
            return await search_channels(client, api_key, country_code, year, seed, max_pages, budget)

    results = await asyncio.gather(*(bounded_search(seed) for seed in queries))
    dedup: dict[str, ChannelRecord] = {}
    for batch in results:
        for record in batch:
            dedup[record.url] = record

    ordered = sorted(dedup.values(), key=lambda item: (item.title.lower(), item.url))
    return country_code, year, ordered


def write_country_year_file(base_dir: Path, country_code: str, year: int, records: list[ChannelRecord]) -> None:
    target = output_path(base_dir, country_code, year)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{record.title} | {record.url}" for record in records]
    target.write_text("\n".join(lines), encoding="utf-8")


async def main() -> None:
    args = parse_args()
    queries = args.queries or DEFAULT_QUERIES
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    budget = QuotaBudget(args.quota_budget)
    summary: dict[str, dict[int, int]] = defaultdict(dict)

    async with httpx.AsyncClient(headers={"Accept": "application/json"}) as client:
        countries = [code.upper() for code in args.countries] if args.countries else await fetch_supported_regions(client, args.api_key)
        semaphore = asyncio.Semaphore(args.concurrency)

        try:
            for country_code in countries:
                for year in year_range(args.start_year, args.end_year):
                    target = output_path(output_dir, country_code, year)
                    if target.exists() and not args.no_resume:
                        print(f"[{country_code}][{year}] skipped existing file")
                        continue

                    _, _, records = await collect_country_year(
                        client,
                        args.api_key,
                        country_code,
                        year,
                        queries,
                        args.max_pages_per_query,
                        semaphore,
                        budget,
                    )
                    write_country_year_file(output_dir, country_code, year, records)
                    summary[country_code][year] = len(records)
                    print(f"[{country_code}][{year}] {len(records)} channels, quota_left={budget.remaining}")
        except QuotaBudgetExceeded as error:
            print(str(error))

    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved summary: {summary_path}")


if __name__ == "__main__":
    asyncio.run(main())
