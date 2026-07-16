#!/usr/bin/env python3
"""Crawl YouTube channels by country/year via Innertube (no personal API key)."""
from __future__ import annotations

import argparse
import asyncio
import json
import random
import re
import string
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

INNERTUBE_URL = "https://www.youtube.com/youtubei/v1"
FALLBACK_API_KEY = "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"
FALLBACK_CLIENT_VERSION = "2.20260714.05.00"
CHANNEL_SEARCH_PARAMS = "EgIQAg%3D%3D"

COUNTRY_NAMES = {
    "VN": "Vietnam",
    "US": "United States",
    "JP": "Japan",
    "KR": "South Korea",
    "GB": "United Kingdom",
    "DE": "Germany",
    "FR": "France",
    "IN": "India",
    "BR": "Brazil",
    "CA": "Canada",
    "TH": "Thailand",
    "ID": "Indonesia",
    "PH": "Philippines",
    "SG": "Singapore",
    "MY": "Malaysia",
    "AU": "Australia",
    "TW": "Taiwan",
    "CN": "China",
}

VN_QUERIES = [
    "viet nam", "vietnam", "vlog viet", "review viet", "tin tuc", "giai tri",
    "am nhac viet", "rap viet", "vpop", "cover viet", "hoc tieng anh",
    "nau an", "meo vat", "hai viet", "phim viet", "game viet", "minecraft",
    "free fire", "lien quan", "roblox", "tiktok", "storytime", "asmr",
    "du lich viet", "sai gon", "ha noi", "da nang", "can tho", "hue",
    "lam giau", "kinh doanh", "crypto", "chung khoan", "bat dong san",
    "cong nghe", "lap trinh", "ai", "review cong nghe", "unbox",
    "tre em", "hoat hinh", "ke chuyen", "giao duc", "toan hoc",
    "lam dep", "thoi trang", "gym", "bong da", "the thao",
    "tin tuc 24h", "vtv", "vtvcab", "yan", "kenh14", "genz",
    "podcast viet", "truyen audio", "nhac tre", "bolero", "remix",
    "o to", "xe may", "phuot", "camping", "nong nghiep",
    "channel", "official", "tv", "news", "music", "gaming", "vlog",
    "kids", "family", "food", "travel", "tech", "beauty", "football",
    "youtube", "live", "shorts", "reaction", "mukbang", "asmr viet",
    "review do an", "spa", "me bau", "nuoi con", "hoc online",
    "tieng viet", "tieng trung", "tieng nhat", "tieng han",
    "piano", "guitar", "hat", "nhay", "dance", "kpop", "usuk",
    "pubg", "lol", "valorant", "fifa", "roblox viet", "minecraft viet",
    "xe", "nha", "cay canh", "thu cung", "meo", "cho",
    "viet", "vn", "hcm", "hn", "cantho", "danang", "nhatrang",
    "review", "unboxing", "tutorial", "howto", "daily", "family vlog",
    "vloggers", "youtuber viet", "kenh youtube", "streamer viet",
    "esport", "lien minh", "toc chien", "genshin", "honkai",
    "anime viet", "manga", "cosplay", "diy", "handmade",
    "noi tro", "meo nau an", "mon ngon", "an vat", "tra sua",
    "skincare", "makeup", "nail", "toc", "thoi trang nam", "thoi trang nu",
    "xe hoi", "xe dap", "xe dien", "bat dong san ha noi", "bat dong san hcm",
    "startup", "marketing", "seo", "dropshipping", "shopee", "lazada",
    "hoc bai", "on thi", "dai hoc", "thpt", "tieng anh giao tiep",
    "phat giao", "cong giao", "tam linh", "phong thuy",
    "ca nhac", "cai luong", "cheo", "cai luong co", "nhac vang",
    "film", "trailer", "phim hay", "phim chieu rap", "phim han",
    "bao moi", "thoi su", "chinh tri", "kinh te", "xa hoi",
    "benh vien", "suc khoe", "bac si", "dong y", "giam can",
    "yeu", "tinh yeu", "hen ho", "gia dinh", "me va be",
    "truyen ma", "kinh di", "hai huoc", "talkshow", "gameshow",
]


def log(msg: str) -> None:
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        print(msg.encode("utf-8", "replace").decode("ascii", "replace"), flush=True)


@dataclass(frozen=True)
class ChannelRecord:
    title: str
    url: str
    channel_id: str
    year: int
    country_code: str


class ClientMeta:
    def __init__(self) -> None:
        self.api_key = FALLBACK_API_KEY
        self.client_version = FALLBACK_CLIENT_VERSION
        self._last_refresh = 0.0

    async def refresh(self, client: httpx.AsyncClient, force: bool = False) -> None:
        now = asyncio.get_event_loop().time()
        if not force and (now - self._last_refresh) < 60:
            return
        try:
            resp = await client.get("https://www.youtube.com/", timeout=30.0)
            resp.raise_for_status()
            html = resp.text
            m_key = re.search(r'"INNERTUBE_API_KEY":"([^"]+)"', html)
            m_ver = re.search(r'"INNERTUBE_CONTEXT_CLIENT_VERSION":"([^"]+)"', html)
            if m_key:
                self.api_key = m_key.group(1)
            if m_ver:
                self.client_version = m_ver.group(1)
            self._last_refresh = now
            log(f"[meta] innertube ok version={self.client_version}")
        except Exception as exc:
            log(f"[meta] fallback key ({exc})")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crawl YouTube channels via Innertube (no personal API key)")
    parser.add_argument("--output-dir", default=".")
    parser.add_argument("--start-year", type=int, default=2005)
    parser.add_argument("--end-year", type=int, default=datetime.now(timezone.utc).year)
    parser.add_argument("--countries", nargs="*", default=["VN"])
    parser.add_argument("--queries", nargs="*")
    parser.add_argument("--max-pages-per-query", type=int, default=10)
    parser.add_argument("--concurrency", type=int, default=6)
    parser.add_argument("--delay", type=float, default=0.2)
    parser.add_argument("--max-channels", type=int, default=0)
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--retry-unknown-only", action="store_true")
    parser.add_argument("--skip-search", action="store_true")
    parser.add_argument("--extra-bigrams", action="store_true")
    return parser.parse_args()


def country_dir_name(code: str) -> str:
    return COUNTRY_NAMES.get(code.upper(), code.upper())


def output_path(base_dir: Path, country_code: str, year: int) -> Path:
    return base_dir / country_dir_name(country_code) / str(year) / "channels.txt"


def unknown_path(base_dir: Path, country_code: str) -> Path:
    return base_dir / country_dir_name(country_code) / "unknown" / "channels.txt"


def discovered_path(base_dir: Path, country_code: str) -> Path:
    return base_dir / country_dir_name(country_code) / "_discovered.json"


def default_queries(country_code: str, extra_bigrams: bool) -> list[str]:
    base = list(string.ascii_lowercase) + list(string.digits)
    if country_code.upper() == "VN":
        seen: set[str] = set()
        out: list[str] = []
        seeds = list(VN_QUERIES) + base
        if extra_bigrams:
            for a in string.ascii_lowercase:
                for b in string.ascii_lowercase:
                    seeds.append(a + b)
        for q in seeds:
            k = q.strip().lower()
            if k and k not in seen:
                seen.add(k)
                out.append(q.strip())
        return out
    return base + ["news", "music", "gaming", "vlog", "official", "tv", "kids", "tech", "sports"]


def client_context(meta: ClientMeta, country_code: str) -> dict[str, Any]:
    hl = "vi" if country_code.upper() == "VN" else "en"
    return {
        "client": {
            "hl": hl,
            "gl": country_code.upper(),
            "clientName": "WEB",
            "clientVersion": meta.client_version,
            "userAgent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
        }
    }


def walk(obj: Any):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from walk(v)
    elif isinstance(obj, list):
        for item in obj:
            yield from walk(item)


def extract_continuation(payload: dict) -> str | None:
    for node in walk(payload):
        cmd = node.get("continuationCommand")
        if isinstance(cmd, dict) and isinstance(cmd.get("token"), str):
            return cmd["token"]
    return None


def extract_channels_from_search(payload: dict) -> list[tuple[str, str]]:
    found: dict[str, str] = {}
    for node in walk(payload):
        ch = node.get("channelRenderer")
        if isinstance(ch, dict):
            cid = ch.get("channelId")
            title = ""
            t = ch.get("title")
            if isinstance(t, dict):
                title = t.get("simpleText") or ""
                if not title and isinstance(t.get("runs"), list):
                    title = "".join(r.get("text", "") for r in t["runs"] if isinstance(r, dict))
            if isinstance(cid, str) and cid.startswith("UC") and title:
                found[cid] = title.strip()
            continue
        cid = node.get("channelId")
        if isinstance(cid, str) and cid.startswith("UC") and len(cid) >= 20:
            title = ""
            if isinstance(node.get("title"), dict):
                title = node["title"].get("simpleText") or ""
                if not title and isinstance(node["title"].get("runs"), list):
                    title = "".join(r.get("text", "") for r in node["title"]["runs"] if isinstance(r, dict))
            if title:
                found.setdefault(cid, title.strip())
    return list(found.items())


def parse_year_from_text(text: str) -> int | None:
    if not text:
        return None
    m = re.search(r"(20\d{2}|200[5-9])", text)
    if m:
        y = int(m.group(1))
        if 2005 <= y <= datetime.now(timezone.utc).year + 1:
            return y
    return None


def year_from_html(html: str) -> int | None:
    patterns = [
        r'"joinedDateText"\s*:\s*\{\s*"content"\s*:\s*"([^"]+)"',
        r'"joinedDateText"\s*:\s*\{[^}]*?"simpleText"\s*:\s*"([^"]+)"',
        r'"joinedDateText"\s*:\s*\{[^}]*?"content"\s*:\s*"([^"]+)"',
        r'(?:Joined|Đã tham gia|Da tham gia)[^0-9]{0,40}(20\d{2}|200[5-9])',
        r'"publishDate"\s*:\s*"(20\d{2}|200[5-9])-\d{2}-\d{2}',
        r'"datePublished"\s*:\s*"(20\d{2}|200[5-9])-\d{2}-\d{2}',
        r'"uploadDate"\s*:\s*"(20\d{2}|200[5-9])-\d{2}-\d{2}',
        r'"startDate"\s*:\s*"(20\d{2}|200[5-9])-\d{2}-\d{2}',
    ]
    for pat in patterns:
        m = re.search(pat, html, flags=re.I)
        if not m:
            continue
        year = parse_year_from_text(m.group(1) if m.lastindex else m.group(0))
        if year:
            return year
    return None


async def innertube_post(
    client: httpx.AsyncClient,
    meta: ClientMeta,
    path: str,
    body: dict,
    semaphore: asyncio.Semaphore,
    delay: float,
) -> dict:
    url = f"{INNERTUBE_URL}{path}?prettyPrint=false&key={meta.api_key}"
    headers = {
        "Content-Type": "application/json",
        "X-YouTube-Client-Name": "1",
        "X-YouTube-Client-Version": meta.client_version,
        "Origin": "https://www.youtube.com",
        "Referer": "https://www.youtube.com/",
    }
    last_err: Exception | None = None
    for attempt in range(4):
        async with semaphore:
            await asyncio.sleep(delay + random.uniform(0, delay * 0.5))
            try:
                resp = await client.post(url, headers=headers, json=body, timeout=45.0)
                if resp.status_code in {429, 500, 502, 503, 504}:
                    await asyncio.sleep(2 ** attempt + random.uniform(0.5, 1.5))
                    continue
                if resp.status_code == 403:
                    await meta.refresh(client)
                    url = f"{INNERTUBE_URL}{path}?prettyPrint=false&key={meta.api_key}"
                    headers["X-YouTube-Client-Version"] = meta.client_version
                    await asyncio.sleep(2.0 + attempt)
                    continue
                resp.raise_for_status()
                return resp.json()
            except Exception as exc:
                last_err = exc
                await asyncio.sleep(1.0 * (attempt + 1))
    if last_err:
        raise last_err
    return {}


async def search_channels(
    client: httpx.AsyncClient,
    meta: ClientMeta,
    country_code: str,
    query: str,
    max_pages: int,
    semaphore: asyncio.Semaphore,
    delay: float,
) -> dict[str, str]:
    results: dict[str, str] = {}
    continuation: str | None = None
    for page in range(max_pages):
        try:
            if page == 0:
                body: dict[str, Any] = {
                    "context": client_context(meta, country_code),
                    "query": query,
                    "params": CHANNEL_SEARCH_PARAMS,
                }
                payload = await innertube_post(client, meta, "/search", body, semaphore, delay)
            else:
                if not continuation:
                    break
                payload = await innertube_post(
                    client,
                    meta,
                    "/search",
                    {"context": client_context(meta, country_code), "continuation": continuation},
                    semaphore,
                    delay,
                )
        except Exception as exc:
            log(f"[{country_code}] search fail q={query!r} page={page}: {exc}")
            break
        for cid, title in extract_channels_from_search(payload):
            results[cid] = title
        continuation = extract_continuation(payload)
        if not continuation:
            break
    return results


async def fetch_channel_year(
    client: httpx.AsyncClient,
    channel_id: str,
    semaphore: asyncio.Semaphore,
    delay: float,
    cache: dict[str, int | None],
) -> int | None:
    """HTML-only year resolve (fast, avoids innertube 403 storm)."""
    if channel_id in cache and cache[channel_id] is not None:
        return cache[channel_id]
    if channel_id in cache and cache[channel_id] is None:
        # allow one re-try when retry-unknown passes clear cache outside
        pass

    year: int | None = None
    url = f"https://www.youtube.com/channel/{channel_id}/about"
    for attempt in range(2):
        try:
            async with semaphore:
                await asyncio.sleep(delay + random.uniform(0, delay * 0.5))
                resp = await client.get(
                    url,
                    headers={"Accept-Language": "en-US,en;q=0.9,vi;q=0.8"},
                    timeout=30.0,
                    follow_redirects=True,
                )
                if resp.status_code in {429, 503}:
                    await asyncio.sleep(3 + attempt * 2)
                    continue
                if resp.status_code == 200 and len(resp.text) > 3000:
                    year = year_from_html(resp.text)
                    if year:
                        cache[channel_id] = year
                        return year
        except Exception:
            await asyncio.sleep(1.0 + attempt)
    cache[channel_id] = None
    return None


def load_existing(base_dir: Path, country_code: str, years: set[int]) -> dict[str, tuple[str, int]]:
    existing: dict[str, tuple[str, int]] = {}
    for year in years:
        path = output_path(base_dir, country_code, year)
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if " | " not in line:
                continue
            title, url = line.rsplit(" | ", 1)
            if url.strip():
                existing[url.strip()] = (title.strip(), year)
    return existing


def load_unknown(base_dir: Path, country_code: str) -> dict[str, str]:
    path = unknown_path(base_dir, country_code)
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if " | " not in line:
            continue
        title, url = line.rsplit(" | ", 1)
        m = re.search(r"/channel/(UC[\w-]+)", url)
        if m:
            out[m.group(1)] = title.strip()
    return out


def load_discovered(base_dir: Path, country_code: str) -> dict[str, str]:
    path = discovered_path(base_dir, country_code)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {k: str(v) for k, v in data.items() if isinstance(k, str) and k.startswith("UC")}
    except Exception:
        pass
    return {}


def save_discovered(base_dir: Path, country_code: str, channels: dict[str, str]) -> None:
    path = discovered_path(base_dir, country_code)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(channels, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")


def write_unknown(base_dir: Path, country_code: str, channels: dict[str, str]) -> int:
    path = unknown_path(base_dir, country_code)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"{title.replace(chr(10), ' ').strip()} | https://www.youtube.com/channel/{cid}"
        for cid, title in sorted(channels.items(), key=lambda x: (x[1].lower(), x[0]))
    ]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return len(lines)


def merge_write(base_dir: Path, country_code: str, year: int, records: list[ChannelRecord], no_resume: bool) -> int:
    target = output_path(base_dir, country_code, year)
    target.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, str] = {}
    if target.exists() and not no_resume:
        for line in target.read_text(encoding="utf-8").splitlines():
            if " | " in line:
                title, url = line.rsplit(" | ", 1)
                if url.strip():
                    existing[url.strip()] = title.strip()
    for rec in records:
        existing[rec.url] = rec.title.replace("\n", " ").strip()
    lines = [f"{title} | {url}" for url, title in sorted(existing.items(), key=lambda x: (x[1].lower(), x[0]))]
    target.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return len(lines)


async def crawl_country(args: argparse.Namespace, country_code: str) -> dict[str, Any]:
    country_code = country_code.upper()
    years = set(range(args.start_year, args.end_year + 1))
    base_dir = Path(args.output_dir)
    country_root = base_dir / country_dir_name(country_code)
    country_root.mkdir(parents=True, exist_ok=True)
    for y in sorted(years):
        p = output_path(base_dir, country_code, y)
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists():
            p.write_text("", encoding="utf-8")

    queries = args.queries or default_queries(country_code, args.extra_bigrams)
    semaphore = asyncio.Semaphore(args.concurrency)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
    }
    meta = ClientMeta()
    year_cache: dict[str, int | None] = {}
    all_channels: dict[str, str] = {}

    if not args.no_resume:
        all_channels.update(load_discovered(base_dir, country_code))
        all_channels.update(load_unknown(base_dir, country_code))
        log(f"[{country_code}] loaded cache discovered+unknown={len(all_channels)}")

    async with httpx.AsyncClient(headers=headers, follow_redirects=True, http2=False) as client:
        await meta.refresh(client, force=True)

        if not args.skip_search and not args.retry_unknown_only:
            log(f"[{country_code}] queries={len(queries)} pages/query={args.max_pages_per_query}")
            for idx, query in enumerate(queries, 1):
                found = await search_channels(
                    client, meta, country_code, query, args.max_pages_per_query, semaphore, args.delay
                )
                before = len(all_channels)
                all_channels.update(found)
                log(
                    f"[{country_code}] [{idx}/{len(queries)}] q={query!r} "
                    f"+{len(all_channels) - before} unique={len(all_channels)}"
                )
                if idx % 10 == 0:
                    save_discovered(base_dir, country_code, all_channels)
                if args.max_channels and len(all_channels) >= args.max_channels:
                    break
            save_discovered(base_dir, country_code, all_channels)
        else:
            log(f"[{country_code}] skip-search/retry-unknown: using {len(all_channels)} cached channels")

        existing = load_existing(base_dir, country_code, years)
        existing_ids: set[str] = set()
        for url in existing:
            m = re.search(r"/channel/(UC[\w-]+)", url)
            if m:
                existing_ids.add(m.group(1))

        if args.retry_unknown_only:
            unk = load_unknown(base_dir, country_code)
            disc = load_discovered(base_dir, country_code)
            todo_map = dict(unk)
            for cid, title in disc.items():
                if cid not in existing_ids:
                    todo_map.setdefault(cid, title)
            todo = list(todo_map.items())
            all_channels.update(todo_map)
            # clear failed year cache for retry
            for cid, _ in todo:
                year_cache.pop(cid, None)
            log(f"[{country_code}] retry-unknown-only todo={len(todo)} (existing_ok={len(existing_ids)})")
        else:
            todo = [(cid, title) for cid, title in all_channels.items() if cid not in existing_ids]
            log(f"[{country_code}] resolve years for {len(todo)} new (skip {len(existing_ids)})")

        save_discovered(base_dir, country_code, all_channels)

        by_year: dict[int, list[ChannelRecord]] = defaultdict(list)
        for url, (title, year) in existing.items():
            m = re.search(r"/channel/(UC[\w-]+)", url)
            cid = m.group(1) if m else url
            by_year[year].append(
                ChannelRecord(title=title, url=url, channel_id=cid, year=year, country_code=country_code)
            )

        unknown_map: dict[str, str] = {}
        done = 0
        unknown = 0
        resolved_ok = 0
        batch_size = 40
        resolve_delay = max(0.12, args.delay * 0.6)

        for i in range(0, len(todo), batch_size):
            batch = todo[i : i + batch_size]
            tasks = [
                fetch_channel_year(client, cid, semaphore, resolve_delay, year_cache)
                for cid, _ in batch
            ]
            years_found = await asyncio.gather(*tasks, return_exceptions=True)
            for (cid, title), y in zip(batch, years_found):
                done += 1
                if isinstance(y, Exception) or y is None:
                    unknown += 1
                    unknown_map[cid] = title
                    continue
                if y not in years:
                    unknown_map[cid] = title
                    continue
                resolved_ok += 1
                url = f"https://www.youtube.com/channel/{cid}"
                by_year[y].append(
                    ChannelRecord(title=title, url=url, channel_id=cid, year=y, country_code=country_code)
                )
            log(
                f"[{country_code}] year-resolve {done}/{len(todo)} "
                f"ok={resolved_ok} unknown={unknown}"
            )
            for year, recs in list(by_year.items()):
                if year in years:
                    merge_write(base_dir, country_code, year, recs, args.no_resume)
            write_unknown(base_dir, country_code, unknown_map)

        unk_count = write_unknown(base_dir, country_code, unknown_map)
        log(f"[{country_code}] unknown remaining={unk_count}")

    summary_years: dict[int, int] = {}
    for year in sorted(years):
        recs = by_year.get(year, [])
        count = merge_write(base_dir, country_code, year, recs, args.no_resume)
        summary_years[year] = count
        log(f"[{country_code}][{year}] {count} channels")
    log(f"[{country_code}] unknown_year={unknown} discovered={len(all_channels)} resolved_ok={resolved_ok}")
    return {
        "years": summary_years,
        "discovered": len(all_channels),
        "unknown": len(unknown_map),
        "resolved_this_run": resolved_ok,
    }


async def main() -> None:
    args = parse_args()
    summary: dict[str, Any] = {}
    for code in args.countries:
        summary[code.upper()] = await crawl_country(args, code)
    out = Path(args.output_dir) / "summary.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"Saved summary: {out}")


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
