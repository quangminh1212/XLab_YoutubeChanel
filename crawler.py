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
CHANNELS_QUOTA_COST = 1
DEFAULT_CONCURRENCY = 6
DEFAULT_MAX_PAGES = 1
DEFAULT_QUOTA_BUDGET = 9_000
DEFAULT_QUERIES = list(string.ascii_lowercase) + list(string.digits)
COUNTRY_NAMES = {
    "US": "United States",
    "VN": "Vietnam",
    "JP": "Japan",
    "KR": "South Korea",
    "GB": "United Kingdom",
    "DE": "Germany",
    "FR": "France",
    "IN": "India",
    "BR": "Brazil",
    "CA": "Canada",
}


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
    year: int
    country_code: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crawl YouTube channels by country and creation year")
    parser.add_argument("--api-key", required=True, help="YouTube Data API key")
    parser.add_argument("--output-dir", default=".", help="Base output directory. Default: repo root")
    parser.add_argument("--start-year", type=int, default=2005, help="Start year. Default: 2005")
    parser.add_argument("--end-year", type=int, default=datetime.now(timezone.utc).year, help="End year. Default: current UTC year")
    parser.add_argument("--countries", nargs="*", default=["VN"], help="ISO-3166-1 alpha-2 country codes. Default: VN")
    parser.add_argument("--queries", nargs="*", help="Search seed queries. Default: a-z 0-9")
    parser.add_argument("--max-pages-per-query", type=int, default=DEFAULT_MAX_PAGES, help="Search pages per query/country. Default: 1")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY, help="Async concurrency. Default: 6")
    parser.add_argument("--quota-budget", type=int, default=DEFAULT_QUOTA_BUDGET, help="Max quota units this run. Default: 9000")
    parser.add_argument("--no-resume", action="store_true", help="Overwrite existing year files instead of preserving them")
    return parser.parse_args()


def country_dir_name(country_code: str) -> str:
    return COUNTRY_NAMES.get(country_code.upper(), country_code.upper())


def output_path(base_dir: Path, country_code: str, year: int) -> Path:
    return base_dir / country_dir_name(country_code) / str(year) / "channels.txt"


def year_range(start_year: int, end_year: int) -> range:
    if start_year > end_year:
        raise ValueError("start-year must be <= end-year")
    return range(start_year, end_year + 1)


def chunked(items: list[str], size: int) -> Iterable[list[str]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


def line_count(path: Path) -> int:
    if not path.exists():
        return 0
    content = path.read_text(encoding="utf-8")
    return content.count("\n") + (1 if content else 0)


def merge_write_records(base_dir: Path, country_code: str, year: int, records: list[ChannelRecord]) -> int:
    target = output_path(base_dir, country_code, year)
    target.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, str] = {}
    if target.exists():
        for line in target.read_text(encoding="utf-8").splitlines():
            if " | " in line:
                title, url = line.rsplit(" | ", 1)
                existing[url] = title
    for record in records:
        existing[record.url] = record.title.replace("\n", " ").strip()
    lines = [f"{title} | {url}" for url, title in sorted(existing.items(), key=lambda item: (item[1].lower(), item[0]))]
    target.write_text("\n".join(lines), encoding="utf-8")
    return len(lines)


async def fetch_json(client: httpx.AsyncClient, path: str, params: dict, budget: QuotaBudget, cost: int) -> dict:
    await budget.spend(cost)
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


async def search_channel_ids(
    client: httpx.AsyncClient,
    api_key: str,
    budget: QuotaBudget,
    country_code: str,
    query: str,
    max_pages: int,
) -> set[str]:
    ids: set[str] = set()
    next_page_token = None
    for _ in range(max_pages):
        params = {
            "part": "snippet",
            "type": "channel",
            "maxResults": 50,
            "q": query,
            "regionCode": country_code,
            "key": api_key,
        }
        if next_page_token:
            params["pageToken"] = next_page_token
        payload = await fetch_json(client, "/search", params, budget, SEARCH_QUOTA_COST)
        for item in payload.get("items", []):
            channel_id = item.get("id", {}).get("channelId") or item.get("snippet", {}).get("channelId")
            if channel_id:
                ids.add(channel_id)
        next_page_token = payload.get("nextPageToken")
        if not next_page_token:
            break
    return ids


async def fetch_channel_records(
    client: httpx.AsyncClient,
    api_key: str,
    budget: QuotaBudget,
    country_code: str,
    channel_ids: list[str],
) -> list[ChannelRecord]:
    if not channel_ids:
        return []
    params = {
        "part": "snippet",
        "id": ",".join(channel_ids),
        "maxResults": 50,
        "key": api_key,
    }
    payload = await fetch_json(client, "/channels", params, budget, CHANNELS_QUOTA_COST)
    records: list[ChannelRecord] = []
    for item in payload.get("items", []):
        snippet = item.get("snippet", {})
        channel_id = item.get("id")
        title = (snippet.get("title") or "").strip()
        published_at = snippet.get("publishedAt") or ""
        if not channel_id or not title or len(published_at) < 4:
            continue
        records.append(
            ChannelRecord(
                title=title,
                url=f"https://www.youtube.com/channel/{channel_id}",
                year=int(published_at[:4]),
                country_code=country_code,
            )
        )
    return records


async def crawl_country(
    client: httpx.AsyncClient,
    args: argparse.Namespace,
    country_code: str,
    years: set[int],
    budget: QuotaBudget,
    semaphore: asyncio.Semaphore,
    summary: dict[str, dict[int, int]],
) -> None:
    queries = args.queries or DEFAULT_QUERIES
    base_dir = Path(args.output_dir)
    channel_ids: set[str] = set()

    async def run_query(seed: str) -> set[str]:
        async with semaphore:
            return await search_channel_ids(client, args.api_key, budget, country_code, seed, args.max_pages_per_query)

    for task in asyncio.as_completed([asyncio.create_task(run_query(seed)) for seed in queries]):
        try:
            channel_ids.update(await task)
        except QuotaBudgetExceeded:
            raise
        except Exception as error:
            print(f"[{country_code}] search error: {error}", flush=True)

    print(f"[{country_code}] found {len(channel_ids)} unique channel ids", flush=True)

    async def run_batch(batch: list[str]) -> list[ChannelRecord]:
        async with semaphore:
            return await fetch_channel_records(client, args.api_key, budget, country_code, batch)

    for task in asyncio.as_completed([asyncio.create_task(run_batch(batch)) for batch in chunked(sorted(channel_ids), 50)]):
        try:
            records = await task
        except QuotaBudgetExceeded:
            raise
        except Exception as error:
            print(f"[{country_code}] channel batch error: {error}", flush=True)
            continue
        by_year: dict[int, list[ChannelRecord]] = defaultdict(list)
        for record in records:
            if record.year in years:
                by_year[record.year].append(record)
        for year, year_records in sorted(by_year.items()):
            count = merge_write_records(base_dir, country_code, year, year_records)
            summary[country_code][year] = count
            print(f"[{country_code}][{year}] {count} channels, quota_left={budget.remaining}", flush=True)

    for year in sorted(years):
        target = output_path(base_dir, country_code, year)
        if not target.exists() or args.no_resume:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.touch(exist_ok=True)
        summary[country_code][year] = line_count(target)


async def main() -> None:
    args = parse_args()
    years = set(year_range(args.start_year, args.end_year))
    budget = QuotaBudget(args.quota_budget)
    semaphore = asyncio.Semaphore(args.concurrency)
    summary: dict[str, dict[int, int]] = defaultdict(dict)
    headers = {"Accept": "application/json", "User-Agent": "XLab-YouTube-Channel-Crawler/1.0"}

    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        try:
            for country_code in [code.upper() for code in args.countries]:
                await crawl_country(client, args, country_code, years, budget, semaphore, summary)
        except QuotaBudgetExceeded as error:
            print(str(error), flush=True)

    summary_path = Path(args.output_dir) / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved summary: {summary_path}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
