import argparse
import asyncio
import json
import re
import string
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote_plus

import httpx


API_BASE = "https://www.googleapis.com/youtube/v3"
YOUTUBE_BASE = "https://www.youtube.com"
SEARCH_QUOTA_COST = 100
DEFAULT_MAX_PAGES = 1
DEFAULT_CONCURRENCY = 6
DEFAULT_QUOTA_BUDGET = 9_000
DEFAULT_QUERIES = list(string.ascii_lowercase) + list(string.digits)
CHANNEL_FILTER_SP = "EgIQAg%3D%3D"
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
    year: int | None
    country_code: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect YouTube channel names and links by country and year")
    parser.add_argument("--mode", choices=["web", "api"], default="web", help="web=no API key, api=YouTube Data API")
    parser.add_argument("--api-key", help="YouTube Data API key (required if --mode api)")
    parser.add_argument("--output-dir", default=".", help="Base output directory. Default: repo root (.)")
    parser.add_argument("--start-year", type=int, default=2005, help="Start year. Default: 2005")
    parser.add_argument("--end-year", type=int, default=datetime.now(timezone.utc).year, help="End year. Default: current UTC year")
    parser.add_argument("--countries", nargs="*", help="ISO-3166-1 alpha-2 country codes. Example: US VN JP")
    parser.add_argument("--max-pages-per-query", type=int, default=DEFAULT_MAX_PAGES, help="Max pages per query. Default: 1")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY, help="Async concurrency. Default: 6")
    parser.add_argument("--quota-budget", type=int, default=DEFAULT_QUOTA_BUDGET, help="Max quota units (api mode). Default: 9000")
    parser.add_argument("--queries", nargs="*", help="Custom search seeds. Default: a-z 0-9")
    parser.add_argument("--no-resume", action="store_true", help="Overwrite existing files instead of skipping")
    return parser.parse_args()


def year_range(start_year: int, end_year: int) -> Iterable[int]:
    if start_year > end_year:
        raise ValueError("start-year must be <= end-year")
    return range(start_year, end_year + 1)


def country_dir_name(country_code: str) -> str:
    return COUNTRY_NAMES.get(country_code.upper(), country_code.upper())


def output_path(base_dir: Path, country_code: str, year: int) -> Path:
    return base_dir / country_dir_name(country_code) / f"{year}.txt"


def extract_json_object(text: str, marker: str) -> dict[str, Any] | None:
    index = text.find(marker)
    if index == -1:
        return None
    start = text.find("{", index)
    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False
    for pos in range(start, len(text)):
        char = text[pos]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : pos + 1])
                except json.JSONDecodeError:
                    return None
    return None


def iter_objects(node: Any):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from iter_objects(value)
    elif isinstance(node, list):
        for item in node:
            yield from iter_objects(item)


def parse_channel_renderer(data: dict[str, Any]) -> tuple[str, str] | None:
    channel_id = data.get("channelId")
    title_runs = data.get("title", {}).get("simpleText")
    if not title_runs:
        runs = data.get("title", {}).get("runs", [])
        title_runs = "".join(part.get("text", "") for part in runs).strip()
    if not channel_id or not title_runs:
        return None
    return title_runs.strip(), f"{YOUTUBE_BASE}/channel/{channel_id}"


def parse_year_from_about_html(html: str) -> int | None:
    data = extract_json_object(html, "var ytInitialData =")
    if not data:
        return None

    for obj in iter_objects(data):
        joined = obj.get("joinedDateText") if isinstance(obj, dict) else None
        if isinstance(joined, dict):
            simple = joined.get("content") or joined.get("simpleText")
            if isinstance(simple, str):
                match = re.search(r"(19|20)\d{2}", simple)
                if match:
                    return int(match.group(0))
            runs = joined.get("runs", [])
            text = " ".join(part.get("text", "") for part in runs if isinstance(part, dict))
            match = re.search(r"(19|20)\d{2}", text)
            if match:
                return int(match.group(0))

    match = re.search(r"(Joined|Đã tham gia)[^\n]{0,40}(19|20)\d{2}", html, flags=re.IGNORECASE)
    if match:
        year_match = re.search(r"(19|20)\d{2}", match.group(0))
        if year_match:
            return int(year_match.group(0))
    return None


async def fetch_text(client: httpx.AsyncClient, url: str, params: dict | None = None) -> str:
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            response = await client.get(url, params=params, timeout=30.0)
            if response.status_code in {429, 500, 502, 503, 504}:
                await asyncio.sleep(2**attempt)
                continue
            response.raise_for_status()
            return response.text
        except (httpx.TimeoutException, httpx.TransportError) as error:
            last_error = error
            await asyncio.sleep(2**attempt)
    if last_error:
        raise last_error
    raise RuntimeError(f"Cannot fetch {url}")


async def fetch_json(client: httpx.AsyncClient, path: str, params: dict, budget: QuotaBudget | None = None) -> dict:
    if path == "/search" and budget:
        await budget.spend(SEARCH_QUOTA_COST)
    response = await client.get(f"{API_BASE}{path}", params=params, timeout=30.0)
    response.raise_for_status()
    return response.json()


async def fetch_supported_regions_api(client: httpx.AsyncClient, api_key: str) -> list[str]:
    payload = await fetch_json(client, "/i18nRegions", {"part": "snippet", "hl": "en_US", "key": api_key})
    regions = sorted({item["snippet"]["gl"] for item in payload.get("items", []) if item.get("snippet", {}).get("gl")})
    if not regions:
        raise RuntimeError("No supported regions returned from YouTube API")
    return regions


async def fetch_supported_regions_web(client: httpx.AsyncClient) -> list[str]:
    html = await fetch_text(client, f"{YOUTUBE_BASE}/i18n")
    codes = sorted(set(re.findall(r'"gl":"([A-Z]{2})"', html)))
    if codes:
        return codes
    return ["US", "VN", "JP", "KR", "GB", "DE", "FR", "IN", "BR", "CA"]


async def search_channels_api(client: httpx.AsyncClient, api_key: str, country_code: str, year: int, query: str, max_pages: int, budget: QuotaBudget) -> list[ChannelRecord]:
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
            if not channel_id or not title:
                continue
            records.append(ChannelRecord(title=title.replace("\n", " "), url=f"{YOUTUBE_BASE}/channel/{channel_id}", year=year, country_code=country_code))

        next_page_token = payload.get("nextPageToken")
        if not next_page_token:
            break
    return records


async def search_channels_web(client: httpx.AsyncClient, country_code: str, query: str, max_pages: int) -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []
    params = {
        "search_query": query,
        "sp": CHANNEL_FILTER_SP,
        "gl": country_code,
        "hl": "en",
    }

    for _ in range(max_pages):
        html = await fetch_text(client, f"{YOUTUBE_BASE}/results", params=params)
        data = extract_json_object(html, "var ytInitialData =")
        if not data:
            break

        for node in iter_objects(data):
            renderer = node.get("channelRenderer") if isinstance(node, dict) else None
            if isinstance(renderer, dict):
                parsed = parse_channel_renderer(renderer)
                if parsed:
                    results.append(parsed)

        break
    dedup: dict[str, str] = {}
    for title, url in results:
        dedup[url] = title
    return [(title, url) for url, title in dedup.items()]


async def enrich_channel_year(client: httpx.AsyncClient, channel_url: str) -> int | None:
    about_url = channel_url.rstrip("/") + "/about"
    html = await fetch_text(client, about_url)
    return parse_year_from_about_html(html)


async def collect_country_web(client: httpx.AsyncClient, country_code: str, years: set[int], queries: list[str], max_pages: int, semaphore: asyncio.Semaphore) -> dict[int, list[ChannelRecord]]:
    channel_map: dict[str, ChannelRecord] = {}

    async def run_query(seed: str):
        async with semaphore:
            return await search_channels_web(client, country_code, seed, max_pages)

    query_results = await asyncio.gather(*(run_query(seed) for seed in queries), return_exceptions=True)
    urls: set[tuple[str, str]] = set()
    for result in query_results:
        if isinstance(result, Exception):
            continue
        urls.update(result)

    async def enrich_one(title: str, url: str):
        async with semaphore:
            try:
                year = await enrich_channel_year(client, url)
            except Exception:
                year = None
            return title, url, year

    enriched = await asyncio.gather(*(enrich_one(title, url) for title, url in urls), return_exceptions=True)
    for item in enriched:
        if isinstance(item, Exception):
            continue
        title, url, year = item
        if year in years:
            channel_map[url] = ChannelRecord(title=title, url=url, year=year, country_code=country_code)

    grouped: dict[int, list[ChannelRecord]] = {year: [] for year in years}
    for record in channel_map.values():
        if record.year in grouped:
            grouped[record.year].append(record)

    for year in grouped:
        grouped[year].sort(key=lambda x: (x.title.lower(), x.url))
    return grouped


def write_country_year_file(base_dir: Path, country_code: str, year: int, records: list[ChannelRecord]) -> None:
    target = output_path(base_dir, country_code, year)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{record.title} | {record.url}" for record in records]
    target.write_text("\n".join(lines), encoding="utf-8")


async def run_api_mode(args: argparse.Namespace, client: httpx.AsyncClient, countries: list[str]) -> dict[str, dict[int, int]]:
    if not args.api_key:
        raise ValueError("--api-key is required when --mode api")

    budget = QuotaBudget(args.quota_budget)
    semaphore = asyncio.Semaphore(args.concurrency)
    summary: dict[str, dict[int, int]] = defaultdict(dict)

    async def collect(country_code: str, year: int, queries: list[str]) -> list[ChannelRecord]:
        async def bounded(seed: str):
            async with semaphore:
                return await search_channels_api(client, args.api_key, country_code, year, seed, args.max_pages_per_query, budget)

        batches = await asyncio.gather(*(bounded(seed) for seed in queries), return_exceptions=True)
        dedup: dict[str, ChannelRecord] = {}
        for batch in batches:
            if isinstance(batch, Exception):
                continue
            for item in batch:
                dedup[item.url] = item
        return sorted(dedup.values(), key=lambda x: (x.title.lower(), x.url))

    try:
        for country_code in countries:
            for year in year_range(args.start_year, args.end_year):
                target = output_path(Path(args.output_dir), country_code, year)
                if target.exists() and not args.no_resume:
                    print(f"[{country_code}][{year}] skipped existing file")
                    continue
                records = await collect(country_code, year, args.queries or DEFAULT_QUERIES)
                write_country_year_file(Path(args.output_dir), country_code, year, records)
                summary[country_code][year] = len(records)
                print(f"[{country_code}][{year}] {len(records)} channels, quota_left={budget.remaining}")
    except QuotaBudgetExceeded as error:
        print(str(error))
    return summary


async def run_web_mode(args: argparse.Namespace, client: httpx.AsyncClient, countries: list[str]) -> dict[str, dict[int, int]]:
    semaphore = asyncio.Semaphore(args.concurrency)
    summary: dict[str, dict[int, int]] = defaultdict(dict)
    queries = args.queries or DEFAULT_QUERIES
    years = set(year_range(args.start_year, args.end_year))
    base_dir = Path(args.output_dir)

    for country_code in countries:
        grouped = await collect_country_web(client, country_code, years, queries, args.max_pages_per_query, semaphore)
        for year in sorted(years):
            target = output_path(base_dir, country_code, year)
            if target.exists() and not args.no_resume:
                print(f"[{country_code}][{year}] skipped existing file")
                continue
            records = grouped.get(year, [])
            write_country_year_file(base_dir, country_code, year, records)
            summary[country_code][year] = len(records)
            print(f"[{country_code}][{year}] {len(records)} channels (web)")
    return summary


async def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    headers = {
        "Accept": "text/html,application/xhtml+xml,application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    }

    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        if args.countries:
            countries = [code.upper() for code in args.countries]
        elif args.mode == "api":
            countries = await fetch_supported_regions_api(client, args.api_key)
        else:
            countries = await fetch_supported_regions_web(client)

        summary = await (run_api_mode(args, client, countries) if args.mode == "api" else run_web_mode(args, client, countries))

    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved summary: {summary_path}")


if __name__ == "__main__":
    asyncio.run(main())

