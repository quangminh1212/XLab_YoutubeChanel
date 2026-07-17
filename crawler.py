#!/usr/bin/env python3
"""Crawl YouTube channels by country/year via Innertube + optional proxy pool."""
from __future__ import annotations

import argparse
import asyncio
import json
import random
import re
import string
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

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

COUNTRY_NAMES = {"VN": "Vietnam"}

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
    "channel", "official", "tv", "news", "music", "gaming", "vlog",
    "kids", "family", "food", "travel", "tech", "beauty", "football",
    "youtube", "live", "shorts", "reaction", "mukbang",
    "viet", "vn", "hcm", "hn", "review", "tutorial", "daily",
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
        now = time.time()
        if not force and (now - self._last_refresh) < 90:
            return
        try:
            resp = await client.get("https://www.youtube.com/", timeout=30.0)
            if resp.status_code != 200:
                return
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
            log(f"[meta] skip refresh ({exc})")


class ProxyPool:
    """Rotate HTTP proxies; mark bad on 429/sorry/connect errors."""

    def __init__(self, proxies: list[str]) -> None:
        # normalize to httpx proxy URL form: http://host:port
        self.proxies: list[str] = []
        for p in proxies:
            p = p.strip()
            if not p:
                continue
            if "://" not in p:
                p = f"http://{p}"
            self.proxies.append(p)
        self.bad: set[str] = set()
        self._idx = 0
        self._lock = asyncio.Lock()
        self.direct_ok = True

    def __len__(self) -> int:
        return len([p for p in self.proxies if p not in self.bad])

    async def next(self) -> str | None:
        async with self._lock:
            alive = [p for p in self.proxies if p not in self.bad]
            if not alive:
                return None
            self._idx = (self._idx + 1) % len(alive)
            return alive[self._idx]

    async def mark_bad(self, proxy: str | None) -> None:
        if not proxy:
            return
        async with self._lock:
            self.bad.add(proxy)
            log(f"[proxy] mark_bad remaining={len(self.proxies) - len(self.bad)}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", default=".")
    p.add_argument("--start-year", type=int, default=2005)
    p.add_argument("--end-year", type=int, default=datetime.now(timezone.utc).year)
    p.add_argument("--countries", nargs="*", default=["VN"])
    p.add_argument("--queries", nargs="*")
    p.add_argument("--max-pages-per-query", type=int, default=8)
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--delay", type=float, default=0.35)
    p.add_argument("--skip-search", action="store_true")
    p.add_argument("--retry-unknown-only", action="store_true")
    p.add_argument("--proxy", default="", help="Single proxy http://host:port or host:port")
    p.add_argument("--proxy-file", default="", help="File with one proxy per line host:port")
    p.add_argument("--fetch-free-proxies", action="store_true", help="Download free HTTP proxies and probe")
    p.add_argument("--max-proxies", type=int, default=40)
    p.add_argument("--prefer-proxy", action="store_true", help="Prefer proxy over direct")
    return p.parse_args()


def country_dir_name(code: str) -> str:
    return COUNTRY_NAMES.get(code.upper(), code.upper())


def output_path(base_dir: Path, country_code: str, year: int) -> Path:
    return base_dir / country_dir_name(country_code) / str(year) / "channels.txt"


def unknown_path(base_dir: Path, country_code: str) -> Path:
    return base_dir / country_dir_name(country_code) / "unknown" / "channels.txt"


def discovered_path(base_dir: Path, country_code: str) -> Path:
    return base_dir / country_dir_name(country_code) / "_discovered.json"


def default_queries() -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for q in VN_QUERIES + list(string.ascii_lowercase) + list(string.digits):
        k = q.strip().lower()
        if k and k not in seen:
            seen.add(k)
            out.append(q.strip())
    return out


def client_context(meta: ClientMeta, country_code: str) -> dict[str, Any]:
    return {
        "client": {
            "hl": "vi" if country_code.upper() == "VN" else "en",
            "gl": country_code.upper(),
            "clientName": "WEB",
            "clientVersion": meta.client_version,
            "userAgent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
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
        cid = node.get("channelId")
        if isinstance(cid, str) and cid.startswith("UC") and len(cid) >= 20:
            title = ""
            if isinstance(node.get("title"), dict):
                title = node["title"].get("simpleText") or ""
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
    if "sorry/index" in html or "Before you continue" in html:
        return None
    patterns = [
        r'"joinedDateText"\s*:\s*\{\s*"content"\s*:\s*"([^"]+)"',
        r'"joinedDateText"\s*:\s*\{[^}]*?"simpleText"\s*:\s*"([^"]+)"',
        r'"joinedDateText"\s*:\s*\{[^}]*?"content"\s*:\s*"([^"]+)"',
        r'(?:Joined|Đã tham gia|Da tham gia)[^0-9]{0,40}(20\d{2}|200[5-9])',
        r'"publishDate"\s*:\s*"(20\d{2}|200[5-9])-\d{2}-\d{2}',
        r'"datePublished"\s*:\s*"(20\d{2}|200[5-9])-\d{2}-\d{2}',
    ]
    for pat in patterns:
        m = re.search(pat, html, flags=re.I)
        if not m:
            continue
        year = parse_year_from_text(m.group(1) if m.lastindex else m.group(0))
        if year:
            return year
    return None


def is_blocked_response(resp: httpx.Response) -> bool:
    if resp.status_code in {429, 403}:
        return True
    url = str(resp.url)
    if "sorry/index" in url or "consent.google" in url:
        return True
    if len(resp.text) < 8000 and ("unusual traffic" in resp.text.lower() or "sorry" in resp.text.lower()):
        return True
    return False


async def fetch_free_proxies(limit: int) -> list[str]:
    urls = [
        "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all&ssl=all&anonymity=all",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
        "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
    ]
    found: list[str] = []
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        for url in urls:
            try:
                r = await client.get(url)
                if r.status_code != 200:
                    continue
                for line in r.text.splitlines():
                    line = line.strip()
                    if re.match(r"^\d+\.\d+\.\d+\.\d+:\d+$", line):
                        found.append(line)
                if len(found) >= limit * 3:
                    break
            except Exception as exc:
                log(f"[proxy] fetch fail {url}: {exc}")
    # shuffle
    random.shuffle(found)
    return found[: limit * 3]


async def probe_proxy(proxy: str, timeout: float = 12.0) -> bool:
    proxy_url = proxy if "://" in proxy else f"http://{proxy}"
    try:
        async with httpx.AsyncClient(
            proxies=proxy_url,
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36"
            },
        ) as client:
            r = await client.get("https://www.youtube.com/")
            if is_blocked_response(r):
                return False
            return r.status_code == 200 and len(r.text) > 50000
    except Exception:
        return False


async def build_proxy_pool(args: argparse.Namespace) -> ProxyPool:
    proxies: list[str] = []
    if args.proxy:
        proxies.append(args.proxy.strip())
    if args.proxy_file:
        path = Path(args.proxy_file)
        if path.exists():
            for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    proxies.append(line)
    if args.fetch_free_proxies:
        log("[proxy] fetching free proxies...")
        free = await fetch_free_proxies(args.max_proxies)
        log(f"[proxy] candidates={len(free)}, probing youtube...")
        sem = asyncio.Semaphore(20)
        ok: list[str] = []

        async def check(p: str) -> None:
            async with sem:
                if await probe_proxy(p):
                    ok.append(p)
                    log(f"[proxy] OK {p} total_ok={len(ok)}")

        await asyncio.gather(*[check(p) for p in free[: max(80, args.max_proxies * 2)]])
        proxies.extend(ok[: args.max_proxies])
        # save working
        out = Path(args.output_dir) / "working_proxies.txt"
        out.write_text("\n".join(ok[: args.max_proxies]) + ("\n" if ok else ""), encoding="utf-8")
        log(f"[proxy] working={len(ok)} saved={out}")

    # unique
    seen: set[str] = set()
    uniq: list[str] = []
    for p in proxies:
        p = p.strip()
        if not p:
            continue
        key = p if "://" in p else f"http://{p}"
        if key not in seen:
            seen.add(key)
            uniq.append(key)
    log(f"[proxy] pool size={len(uniq)}")
    return ProxyPool(uniq)


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


def merge_write(base_dir: Path, country_code: str, year: int, records: list[ChannelRecord]) -> int:
    target = output_path(base_dir, country_code, year)
    target.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, str] = {}
    if target.exists():
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


async def make_client(proxy: str | None, timeout: float = 35.0) -> httpx.AsyncClient:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
    }
    kwargs: dict[str, Any] = {
        "headers": headers,
        "follow_redirects": True,
        "http2": False,
        "timeout": timeout,
    }
    if proxy:
        kwargs["proxies"] = proxy
    return httpx.AsyncClient(**kwargs)


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
            await asyncio.sleep(delay + random.uniform(0, delay * 0.4))
            try:
                resp = await client.post(url, headers=headers, json=body)
                if resp.status_code in {429, 500, 502, 503, 504}:
                    await asyncio.sleep(2 ** attempt + 1)
                    continue
                if resp.status_code == 403:
                    await meta.refresh(client)
                    await asyncio.sleep(2)
                    continue
                resp.raise_for_status()
                return resp.json()
            except Exception as exc:
                last_err = exc
                await asyncio.sleep(1.2 * (attempt + 1))
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
                body = {
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
            log(f"[{country_code}] search fail q={query!r}: {exc}")
            break
        for cid, title in extract_channels_from_search(payload):
            results[cid] = title
        continuation = extract_continuation(payload)
        if not continuation:
            break
    return results


async def refresh_pool_if_low(pool: ProxyPool, min_alive: int = 3, max_new: int = 15) -> None:
    if len(pool) >= min_alive:
        return
    log(f"[proxy] pool low ({len(pool)}), fetching more free proxies...")
    candidates = await fetch_free_proxies(max_new * 3)
    random.shuffle(candidates)
    sem = asyncio.Semaphore(15)
    added = 0

    async def check(p: str) -> None:
        nonlocal added
        async with sem:
            if await probe_proxy(p):
                key = p if "://" in p else f"http://{p}"
                if key not in pool.proxies and key not in pool.bad:
                    pool.proxies.append(key)
                    added += 1
                    log(f"[proxy] refill OK {p} alive={len(pool)}")

    await asyncio.gather(*[check(p) for p in candidates[:60]])
    # persist
    try:
        Path("working_proxies.txt").write_text(
            "\n".join(pool.proxies) + ("\n" if pool.proxies else ""),
            encoding="utf-8",
        )
    except Exception:
        pass
    log(f"[proxy] refill done added={added} alive={len(pool)}")


async def fetch_channel_year(
    channel_id: str,
    pool: ProxyPool,
    semaphore: asyncio.Semaphore,
    delay: float,
    cache: dict[str, int | None],
    prefer_proxy: bool,
) -> int | None:
    if channel_id in cache and cache[channel_id] is not None:
        return cache[channel_id]

    url = f"https://www.youtube.com/channel/{channel_id}/about"
    # Order: direct first (unless prefer_proxy), then proxies, then direct again
    modes: list[str | None] = []
    if prefer_proxy and len(pool):
        modes = [await pool.next(), None, await pool.next(), await pool.next()]
    else:
        modes = [None]
        if len(pool):
            modes.extend([await pool.next(), await pool.next()])
        modes.append(None)

    for attempt, proxy in enumerate(modes):
        try:
            async with semaphore:
                await asyncio.sleep(delay + random.uniform(0, delay * 0.4))
                async with await make_client(proxy) as client:
                    resp = await client.get(url)
                    if is_blocked_response(resp):
                        if proxy:
                            await pool.mark_bad(proxy)
                        else:
                            # direct blocked: backoff
                            await asyncio.sleep(4 + attempt * 2)
                        continue
                    if resp.status_code == 200 and len(resp.text) > 5000:
                        year = year_from_html(resp.text)
                        if year:
                            cache[channel_id] = year
                            return year
        except Exception:
            if proxy:
                await pool.mark_bad(proxy)
            await asyncio.sleep(0.4 + attempt * 0.3)
    cache[channel_id] = None
    return None


async def crawl_country(args: argparse.Namespace, country_code: str, pool: ProxyPool) -> dict[str, Any]:
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

    all_channels: dict[str, str] = {}
    all_channels.update(load_discovered(base_dir, country_code))
    all_channels.update(load_unknown(base_dir, country_code))
    log(f"[{country_code}] cache={len(all_channels)} proxies={len(pool)}")

    meta = ClientMeta()
    semaphore = asyncio.Semaphore(args.concurrency)
    year_cache: dict[str, int | None] = {}

    # search client: prefer direct, fallback proxy
    search_proxy = await pool.next() if (args.prefer_proxy and len(pool)) else None
    async with await make_client(search_proxy) as client:
        await meta.refresh(client, force=True)
        if not args.skip_search and not args.retry_unknown_only:
            queries = args.queries or default_queries()
            log(f"[{country_code}] search queries={len(queries)}")
            for idx, query in enumerate(queries, 1):
                found = await search_channels(
                    client, meta, country_code, query, args.max_pages_per_query, semaphore, args.delay
                )
                before = len(all_channels)
                all_channels.update(found)
                log(f"[{country_code}] [{idx}/{len(queries)}] q={query!r} +{len(all_channels)-before} unique={len(all_channels)}")
                if idx % 10 == 0:
                    save_discovered(base_dir, country_code, all_channels)
            save_discovered(base_dir, country_code, all_channels)
        else:
            log(f"[{country_code}] skip-search using cache")

    existing = load_existing(base_dir, country_code, years)
    existing_ids: set[str] = set()
    for url in existing:
        m = re.search(r"/channel/(UC[\w-]+)", url)
        if m:
            existing_ids.add(m.group(1))

    if args.retry_unknown_only:
        todo_map = dict(load_unknown(base_dir, country_code))
        for cid, title in load_discovered(base_dir, country_code).items():
            if cid not in existing_ids:
                todo_map.setdefault(cid, title)
        todo = list(todo_map.items())
        for cid, _ in todo:
            year_cache.pop(cid, None)
    else:
        todo = [(cid, title) for cid, title in all_channels.items() if cid not in existing_ids]

    log(f"[{country_code}] resolve todo={len(todo)} existing={len(existing_ids)}")
    save_discovered(base_dir, country_code, all_channels)

    by_year: dict[int, list[ChannelRecord]] = defaultdict(list)
    for url, (title, year) in existing.items():
        m = re.search(r"/channel/(UC[\w-]+)", url)
        cid = m.group(1) if m else url
        by_year[year].append(ChannelRecord(title=title, url=url, channel_id=cid, year=year, country_code=country_code))

    unknown_map: dict[str, str] = {}
    done = 0
    ok = 0
    unknown = 0
    batch_size = 30

    for i in range(0, len(todo), batch_size):
        # refill free proxies when nearly empty
        if (i // batch_size) % 3 == 0:
            await refresh_pool_if_low(pool, min_alive=3, max_new=20)

        batch = todo[i : i + batch_size]
        tasks = [
            fetch_channel_year(cid, pool, semaphore, args.delay, year_cache, args.prefer_proxy)
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
            ok += 1
            # resolved: drop from unknown map if present
            unknown_map.pop(cid, None)
            by_year[y].append(
                ChannelRecord(
                    title=title,
                    url=f"https://www.youtube.com/channel/{cid}",
                    channel_id=cid,
                    year=y,
                    country_code=country_code,
                )
            )
        log(f"[{country_code}] year-resolve {done}/{len(todo)} ok={ok} unknown={unknown} proxies_left={len(pool)}")
        for year, recs in list(by_year.items()):
            if year in years:
                merge_write(base_dir, country_code, year, recs)
        write_unknown(base_dir, country_code, unknown_map)
        # gentle pause every batch to reduce ban risk
        await asyncio.sleep(0.8)

    unk_count = write_unknown(base_dir, country_code, unknown_map)
    summary_years: dict[int, int] = {}
    for year in sorted(years):
        count = merge_write(base_dir, country_code, year, by_year.get(year, []))
        summary_years[year] = count
        log(f"[{country_code}][{year}] {count}")
    log(f"[{country_code}] done ok={ok} unknown={unk_count} discovered={len(all_channels)}")
    return {"years": summary_years, "discovered": len(all_channels), "unknown": unk_count, "resolved_ok": ok}


async def main() -> None:
    args = parse_args()
    pool = await build_proxy_pool(args)
    summary: dict[str, Any] = {}
    for code in args.countries:
        summary[code.upper()] = await crawl_country(args, code, pool)
    out = Path(args.output_dir) / "summary.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"Saved summary: {out}")


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
