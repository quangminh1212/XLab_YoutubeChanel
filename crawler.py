#!/usr/bin/env python3
"""Crawl Vietnam YouTube channels with subscriber filter (default >= 1000)."""
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
from dataclasses import asdict, dataclass
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
COUNTRY = "VN"
COUNTRY_DIR = "Vietnam"

# Broad VN-oriented seeds for higher coverage
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
    "ca nhac", "cai luong", "cheo", "nhac vang",
    "film", "trailer", "phim hay", "phim chieu rap", "phim han",
    "bao moi", "thoi su", "chinh tri", "kinh te", "xa hoi",
    "benh vien", "suc khoe", "bac si", "dong y", "giam can",
    "yeu", "tinh yeu", "hen ho", "gia dinh", "me va be",
    "truyen ma", "kinh di", "hai huoc", "talkshow", "gameshow",
    "hai phong", "quang ninh", "binh duong", "dong nai", "vung tau",
    "an giang", "kien giang", "ca mau", "lam dong", "da lat",
    "nghe an", "thanh hoa", "quang nam", "quang ngai", "binh dinh",
    "phu yen", "khanh hoa", "ninh thuan", "binh thuan", "tay ninh",
    "long an", "tien giang", "ben tre", "tra vinh", "vinh long",
    "dong thap", "soc trang", "bac ninh", "bac giang", "hung yen",
    "nam dinh", "thai binh", "ha nam", "ninh binh", "hoa binh",
    "son la", "dien bien", "lai chau", "lao cai", "yen bai",
    "tuyen quang", "ha giang", "cao bang", "bac kan", "lang son",
    "thai nguyen", "phu tho", "vinh phuc", "quang tri", "thua thien hue",
    "kon tum", "gia lai", "dak lak", "dak nong",
    "youtuber", "streamer", "reviewer", "tiktoker", "kol", "influencer",
    "giai tri viet", "am thuc viet", "van hoa viet", "lich su viet",
    "nhac che", "nhac che viet", "remix viet", "edmviet",
    "freefire viet", "lien quan mobile", "toc chien viet",
    "hoc tieng han", "hoc tieng nhat", "hoc tieng trung",
    "meo hay", "doi song", "tieu thuong", "kinh doanh online",
]


def log(msg: str) -> None:
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        print(msg.encode("utf-8", "replace").decode("ascii", "replace"), flush=True)


@dataclass
class ChannelInfo:
    channel_id: str
    title: str
    url: str
    year: int | None = None
    subscribers: int | None = None


class ClientMeta:
    def __init__(self) -> None:
        self.api_key = FALLBACK_API_KEY
        self.client_version = FALLBACK_CLIENT_VERSION
        self._last = 0.0

    async def refresh(self, client: httpx.AsyncClient, force: bool = False) -> None:
        now = time.time()
        if not force and now - self._last < 90:
            return
        try:
            r = await client.get("https://www.youtube.com/", timeout=30)
            if r.status_code != 200:
                return
            m_key = re.search(r'"INNERTUBE_API_KEY":"([^"]+)"', r.text)
            m_ver = re.search(r'"INNERTUBE_CONTEXT_CLIENT_VERSION":"([^"]+)"', r.text)
            if m_key:
                self.api_key = m_key.group(1)
            if m_ver:
                self.client_version = m_ver.group(1)
            self._last = now
            log(f"[meta] ok {self.client_version}")
        except Exception as e:
            log(f"[meta] {e}")


class ProxyPool:
    def __init__(self, proxies: list[str] | None = None) -> None:
        self.proxies: list[str] = []
        self.bad: set[str] = set()
        self._i = 0
        self._lock = asyncio.Lock()
        for p in proxies or []:
            p = p.strip()
            if not p:
                continue
            if "://" not in p:
                p = f"http://{p}"
            self.proxies.append(p)

    def __len__(self) -> int:
        return len([p for p in self.proxies if p not in self.bad])

    async def next(self) -> str | None:
        async with self._lock:
            alive = [p for p in self.proxies if p not in self.bad]
            if not alive:
                return None
            self._i = (self._i + 1) % len(alive)
            return alive[self._i]

    async def mark_bad(self, proxy: str | None) -> None:
        if proxy:
            async with self._lock:
                self.bad.add(proxy)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", default=".")
    p.add_argument("--min-subs", type=int, default=1000)
    p.add_argument("--start-year", type=int, default=2005)
    p.add_argument("--end-year", type=int, default=datetime.now(timezone.utc).year)
    p.add_argument("--max-pages-per-query", type=int, default=10)
    p.add_argument("--concurrency", type=int, default=32)
    p.add_argument("--delay", type=float, default=0.05)
    p.add_argument("--batch-size", type=int, default=160)
    p.add_argument("--skip-search", action="store_true")
    p.add_argument("--enrich-only", action="store_true", help="Only enrich known ids (discovered+existing)")
    p.add_argument("--fetch-free-proxies", action="store_true")
    p.add_argument("--proxy-file", default="working_proxies.txt")
    p.add_argument("--max-proxies", type=int, default=20)
    p.add_argument("--extra-bigrams", action="store_true")
    return p.parse_args()


def default_queries(extra_bigrams: bool) -> list[str]:
    seeds = list(VN_QUERIES) + list(string.ascii_lowercase) + list(string.digits)
    if extra_bigrams:
        for a in string.ascii_lowercase:
            for b in "aeiouy":
                seeds.append(a + b)
    out, seen = [], set()
    for q in seeds:
        k = q.strip().lower()
        if k and k not in seen:
            seen.add(k)
            out.append(q.strip())
    return out


def walk(obj: Any):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from walk(v)
    elif isinstance(obj, list):
        for i in obj:
            yield from walk(i)


def extract_continuation(payload: dict) -> str | None:
    for node in walk(payload):
        cmd = node.get("continuationCommand")
        if isinstance(cmd, dict) and isinstance(cmd.get("token"), str):
            return cmd["token"]
    return None


def extract_channels_from_search(payload: dict) -> dict[str, str]:
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
    return found


def parse_year_from_text(text: str) -> int | None:
    m = re.search(r"(20\d{2}|200[5-9])", text or "")
    if not m:
        return None
    y = int(m.group(1))
    if 2005 <= y <= datetime.now(timezone.utc).year + 1:
        return y
    return None


def parse_subscriber_count(text: str) -> int | None:
    if not text:
        return None
    t = text.strip().replace("\xa0", " ")
    # exact digits
    m = re.search(r"([\d][\d,\.\s]*)\s*(K|M|B|N|Tr|Tỷ|ty|nghìn|nghin|triệu|trieu|tr|k|m|b)?", t, re.I)
    if not m:
        # "No subscribers"
        if re.search(r"no subscribers|chưa có|chua co", t, re.I):
            return 0
        return None
    num_s = m.group(1).replace(" ", "").replace(",", "")
    # European style 1.234.567
    if num_s.count(".") > 1:
        num_s = num_s.replace(".", "")
    elif num_s.count(".") == 1 and len(num_s.split(".")[-1]) == 3 and "K" not in t.upper() and "M" not in t.upper():
        # could be thousand separator
        left, right = num_s.split(".")
        if len(right) == 3:
            num_s = left + right
    try:
        num = float(num_s)
    except ValueError:
        return None
    unit = (m.group(2) or "").lower()
    mult = 1
    if unit in {"k", "n", "nghìn", "nghin"}:
        mult = 1_000
    elif unit in {"m", "tr", "triệu", "trieu"}:
        mult = 1_000_000
    elif unit in {"b", "tỷ", "ty"}:
        mult = 1_000_000_000
    return int(num * mult)


def year_from_html(html: str) -> int | None:
    if "sorry/index" in html:
        return None
    for pat in [
        r'"joinedDateText"\s*:\s*\{\s*"content"\s*:\s*"([^"]+)"',
        r'"joinedDateText"\s*:\s*\{[^}]*?"simpleText"\s*:\s*"([^"]+)"',
        r'(?:Joined|Đã tham gia|Da tham gia)[^0-9]{0,40}(20\d{2}|200[5-9])',
        r'"publishDate"\s*:\s*"(20\d{2}|200[5-9])-\d{2}-\d{2}',
    ]:
        m = re.search(pat, html, re.I)
        if m:
            y = parse_year_from_text(m.group(1) if m.lastindex else m.group(0))
            if y:
                return y
    return None


def subs_from_html(html: str) -> int | None:
    if "sorry/index" in html:
        return None
    patterns = [
        r'"subscriberCountText"\s*:\s*"([^"]+)"',
        r'"subscriberCountText"\s*:\s*\{\s*"simpleText"\s*:\s*"([^"]+)"',
        r'"subscriberCountText"\s*:\s*\{[^}]*?"content"\s*:\s*"([^"]+)"',
        r'"subscriberCountText"\s*:\s*\{[^}]*?"accessibility"\s*:\s*\{\s*"accessibilityData"\s*:\s*\{\s*"label"\s*:\s*"([^"]+)"',
        r'"subscriberCount"\s*:\s*"(\d+)"',
        # newer UI: plain content/simpleText/label with "X subscribers"
        r'"content"\s*:\s*"([^"]*?\bsubscribers?\b[^"]*)"',
        r'"simpleText"\s*:\s*"([^"]*?\bsubscribers?\b[^"]*)"',
        r'"label"\s*:\s*"([^"]*?\bsubscribers?\b[^"]*)"',
        r'"content"\s*:\s*"([^"]*?(?:người đăng ký|nguoi dang ky)[^"]*)"',
        r'"simpleText"\s*:\s*"([^"]*?(?:người đăng ký|nguoi dang ky)[^"]*)"',
    ]
    for pat in patterns:
        m = re.search(pat, html, re.I)
        if not m:
            continue
        raw = m.group(1)
        if raw.isdigit():
            return int(raw)
        n = parse_subscriber_count(raw)
        if n is not None:
            return n
    return None


def is_blocked(resp: httpx.Response) -> bool:
    if resp.status_code in {429, 403}:
        return True
    u = str(resp.url)
    if "sorry/index" in u:
        return True
    if len(resp.text) < 8000 and "unusual traffic" in resp.text.lower():
        return True
    return False


async def make_client(proxy: str | None = None, timeout: float = 14.0) -> httpx.AsyncClient:
    kwargs: dict[str, Any] = {
        "headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
        },
        "follow_redirects": True,
        "timeout": timeout,
        "http2": False,
        "limits": httpx.Limits(max_connections=200, max_keepalive_connections=80),
    }
    if proxy:
        kwargs["proxies"] = proxy
    return httpx.AsyncClient(**kwargs)


async def fetch_free_proxies(limit: int) -> list[str]:
    urls = [
        "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all&ssl=all&anonymity=all",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    ]
    found: list[str] = []
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as c:
        for url in urls:
            try:
                r = await c.get(url)
                if r.status_code != 200:
                    continue
                for line in r.text.splitlines():
                    line = line.strip()
                    if re.match(r"^\d+\.\d+\.\d+\.\d+:\d+$", line):
                        found.append(line)
            except Exception:
                pass
    random.shuffle(found)
    return found[: limit * 4]


async def probe_proxy(proxy: str) -> bool:
    p = proxy if "://" in proxy else f"http://{proxy}"
    try:
        kwargs: dict[str, Any] = {
            "headers": {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
                ),
            },
            "follow_redirects": True,
            "timeout": 8.0,
            "proxies": p,
        }
        async with httpx.AsyncClient(**kwargs) as c:
            r = await c.get("https://www.youtube.com/")
            return (not is_blocked(r)) and r.status_code == 200 and len(r.text) > 20000
    except Exception:
        return False


async def build_pool(args: argparse.Namespace) -> ProxyPool:
    proxies: list[str] = []
    pf = Path(args.proxy_file)
    if pf.exists():
        proxies.extend([ln.strip() for ln in pf.read_text(encoding="utf-8", errors="ignore").splitlines() if ln.strip()])
    if args.fetch_free_proxies:
        log("[proxy] fetching free proxies...")
        cands = await fetch_free_proxies(args.max_proxies)
        log(f"[proxy] candidates={len(cands)}")
        sem = asyncio.Semaphore(20)
        ok: list[str] = []

        async def chk(p: str) -> None:
            async with sem:
                if await probe_proxy(p):
                    ok.append(p)
                    log(f"[proxy] OK {p} total={len(ok)}")

        # cap probe set so startup stays fast under high concurrency runs
        probe_n = min(48, max(16, args.max_proxies * 2))
        await asyncio.gather(*[chk(p) for p in cands[:probe_n]])
        proxies.extend(ok[: args.max_proxies])
        Path(args.output_dir, "working_proxies.txt").write_text("\n".join(ok[: args.max_proxies]) + "\n", encoding="utf-8")
        log(f"[proxy] working={len(ok[:args.max_proxies])}")
    # unique
    seen, uniq = set(), []
    for p in proxies:
        k = p if "://" in p else f"http://{p}"
        if k not in seen:
            seen.add(k)
            uniq.append(k)
    log(f"[proxy] pool={len(uniq)}")
    return ProxyPool(uniq)


async def innertube_post(client: httpx.AsyncClient, meta: ClientMeta, path: str, body: dict, sem: asyncio.Semaphore, delay: float) -> dict:
    url = f"{INNERTUBE_URL}{path}?prettyPrint=false&key={meta.api_key}"
    headers = {
        "Content-Type": "application/json",
        "X-YouTube-Client-Name": "1",
        "X-YouTube-Client-Version": meta.client_version,
        "Origin": "https://www.youtube.com",
        "Referer": "https://www.youtube.com/",
    }
    last = None
    for attempt in range(4):
        async with sem:
            await asyncio.sleep(delay + random.uniform(0, delay * 0.3))
            try:
                r = await client.post(url, headers=headers, json=body)
                if r.status_code in {429, 500, 502, 503, 504}:
                    await asyncio.sleep(2 ** attempt)
                    continue
                if r.status_code == 403:
                    await meta.refresh(client)
                    await asyncio.sleep(2)
                    continue
                r.raise_for_status()
                return r.json()
            except Exception as e:
                last = e
                await asyncio.sleep(1 + attempt)
    if last:
        raise last
    return {}


async def search_channels(client: httpx.AsyncClient, meta: ClientMeta, query: str, pages: int, sem: asyncio.Semaphore, delay: float) -> dict[str, str]:
    found: dict[str, str] = {}
    cont = None
    for page in range(pages):
        try:
            if page == 0:
                body = {
                    "context": {
                        "client": {
                            "hl": "vi",
                            "gl": "VN",
                            "clientName": "WEB",
                            "clientVersion": meta.client_version,
                        }
                    },
                    "query": query,
                    "params": CHANNEL_SEARCH_PARAMS,
                }
                payload = await innertube_post(client, meta, "/search", body, sem, delay)
            else:
                if not cont:
                    break
                payload = await innertube_post(
                    client,
                    meta,
                    "/search",
                    {
                        "context": {
                            "client": {
                                "hl": "vi",
                                "gl": "VN",
                                "clientName": "WEB",
                                "clientVersion": meta.client_version,
                            }
                        },
                        "continuation": cont,
                    },
                    sem,
                    delay,
                )
        except Exception as e:
            log(f"[search] fail q={query!r}: {e}")
            break
        found.update(extract_channels_from_search(payload))
        cont = extract_continuation(payload)
        if not cont:
            break
    return found


def _apply_about_html(info: ChannelInfo, html: str) -> ChannelInfo:
    y = year_from_html(html)
    s = subs_from_html(html)
    if y is not None:
        info.year = y
    if s is not None:
        info.subscribers = s
    if not info.title or info.title == info.channel_id:
        mt = re.search(r'"channelMetadataRenderer"\s*:\s*\{[^}]*?"title"\s*:\s*"([^"]+)"', html)
        if mt:
            info.title = mt.group(1)
    return info


async def enrich_channel(
    channel_id: str,
    title: str,
    pool: ProxyPool,
    sem: asyncio.Semaphore,
    delay: float,
    cache: dict[str, ChannelInfo],
    shared_client: httpx.AsyncClient | None = None,
) -> ChannelInfo:
    if channel_id in cache and cache[channel_id].subscribers is not None and cache[channel_id].year is not None:
        return cache[channel_id]

    info = cache.get(channel_id) or ChannelInfo(
        channel_id=channel_id,
        title=title,
        url=f"https://www.youtube.com/channel/{channel_id}",
    )
    if title and (not info.title or info.title == channel_id):
        info.title = title

    url = f"https://www.youtube.com/channel/{channel_id}/about"

    async with sem:
        if delay > 0:
            await asyncio.sleep(delay + random.uniform(0, max(0.005, delay * 0.25)))
        # 1) shared direct client (fast path)
        if shared_client is not None:
            try:
                r = await asyncio.wait_for(shared_client.get(url), timeout=8.0)
                if not is_blocked(r) and r.status_code == 200 and len(r.text) > 5000:
                    info = _apply_about_html(info, r.text)
                    if info.year is not None and info.subscribers is not None:
                        cache[channel_id] = info
                        return info
            except Exception:
                pass
        # 2) one-shot direct
        try:
            async with await make_client(None, timeout=8.0) as client:
                r = await client.get(url)
                if not is_blocked(r) and r.status_code == 200 and len(r.text) > 5000:
                    info = _apply_about_html(info, r.text)
                    if info.year is not None and info.subscribers is not None:
                        cache[channel_id] = info
                        return info
        except Exception:
            pass
        # 3) one proxy fallback
        if len(pool):
            proxy = await pool.next()
            try:
                async with await make_client(proxy, timeout=7.0) as client:
                    r = await client.get(url)
                    if is_blocked(r):
                        await pool.mark_bad(proxy)
                    elif r.status_code == 200 and len(r.text) > 5000:
                        info = _apply_about_html(info, r.text)
                        if info.year is not None and info.subscribers is not None:
                            cache[channel_id] = info
                            return info
            except Exception:
                await pool.mark_bad(proxy)

    cache[channel_id] = info
    return info


def load_discovered(base: Path) -> dict[str, str]:
    p = base / COUNTRY_DIR / "_discovered.json"
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return {k: str(v) for k, v in data.items() if isinstance(k, str) and k.startswith("UC")}
    except Exception:
        return {}


def load_ids_from_year_files(base: Path) -> dict[str, str]:
    """Load ids from Vietnam/YYYY.txt (new) and legacy Vietnam/YYYY/channels.txt."""
    out: dict[str, str] = {}
    root = base / COUNTRY_DIR
    if not root.exists():
        return out
    files: list[Path] = []
    for p in root.iterdir():
        if p.is_file() and re.match(r"^\d{4}\.txt$", p.name):
            files.append(p)
        elif p.is_dir() and p.name.isdigit():
            f = p / "channels.txt"
            if f.exists():
                files.append(f)
    for f in files:
        for line in f.read_text(encoding="utf-8").splitlines():
            if " | " not in line:
                continue
            # support title | url and title | url | subs [| year]
            parts = [x.strip() for x in line.split(" | ")]
            if len(parts) < 2:
                continue
            title, url = parts[0], parts[1]
            m = re.search(r"/channel/(UC[\w-]+)", url)
            if m:
                out[m.group(1)] = title
    return out


def load_enrich_cache(base: Path) -> dict[str, ChannelInfo]:
    p = base / COUNTRY_DIR / "_enriched.json"
    out: dict[str, ChannelInfo] = {}
    if not p.exists():
        return out
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        for cid, obj in data.items():
            out[cid] = ChannelInfo(
                channel_id=cid,
                title=obj.get("title") or cid,
                url=obj.get("url") or f"https://www.youtube.com/channel/{cid}",
                year=obj.get("year"),
                subscribers=obj.get("subscribers"),
            )
    except Exception:
        pass
    return out


def save_enrich_cache(base: Path, cache: dict[str, ChannelInfo]) -> None:
    p = base / COUNTRY_DIR / "_enriched.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {cid: asdict(info) for cid, info in cache.items()}
    p.write_text(json.dumps(data, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")


def save_discovered(base: Path, channels: dict[str, str]) -> None:
    p = base / COUNTRY_DIR / "_discovered.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(channels, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")


def write_outputs(base: Path, cache: dict[str, ChannelInfo], min_subs: int, years: set[int]) -> dict[str, Any]:
    """Write one file per year: Vietnam/YYYY.txt (not Vietnam/YYYY/channels.txt)."""
    root = base / COUNTRY_DIR
    root.mkdir(parents=True, exist_ok=True)

    # remove legacy year folders if any
    for d in list(root.iterdir()):
        if d.is_dir() and d.name.isdigit():
            try:
                import shutil

                shutil.rmtree(d, ignore_errors=True)
            except Exception:
                pass

    by_year: dict[int, list[ChannelInfo]] = defaultdict(list)
    below: list[ChannelInfo] = []
    unknown: list[ChannelInfo] = []
    for info in cache.values():
        if info.subscribers is None or info.year is None:
            unknown.append(info)
            continue
        if info.subscribers < min_subs:
            below.append(info)
            continue
        if info.year in years:
            by_year[info.year].append(info)

    for y in sorted(years):
        recs = sorted(by_year.get(y, []), key=lambda x: (-(x.subscribers or 0), x.title.lower()))
        lines = [
            f"{(r.title or r.channel_id).replace(chr(10), ' ').strip()} | {r.url} | {r.subscribers}"
            for r in recs
        ]
        (root / f"{y}.txt").write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    # below 1000 archive as single file
    below_sorted = sorted(below, key=lambda x: (-(x.subscribers or 0), x.title.lower()))
    (root / "below_1000.txt").write_text(
        "\n".join(
            f"{(r.title or r.channel_id).replace(chr(10),' ').strip()} | {r.url} | {r.subscribers} | {r.year}"
            for r in below_sorted
        )
        + ("\n" if below_sorted else ""),
        encoding="utf-8",
    )

    (root / "unknown.txt").write_text(
        "\n".join(
            f"{(r.title or r.channel_id).replace(chr(10),' ').strip()} | {r.url}"
            for r in sorted(unknown, key=lambda x: x.title.lower())
        )
        + ("\n" if unknown else ""),
        encoding="utf-8",
    )
    # drop legacy unknown/ folder if present
    unk_dir = root / "unknown"
    if unk_dir.is_dir():
        try:
            import shutil

            shutil.rmtree(unk_dir, ignore_errors=True)
        except Exception:
            pass

    # flat min1k list
    all_min: list[ChannelInfo] = []
    for y in sorted(by_year):
        all_min.extend(by_year[y])
    all_min.sort(key=lambda x: (-(x.subscribers or 0), x.title.lower()))
    (root / "channels_min1000.txt").write_text(
        "\n".join(
            f"{(r.title or r.channel_id).replace(chr(10),' ').strip()} | {r.url} | {r.subscribers} | {r.year}"
            for r in all_min
        )
        + ("\n" if all_min else ""),
        encoding="utf-8",
    )

    summary = {
        "min_subs": min_subs,
        "layout": "Vietnam/YYYY.txt",
        "total_enriched": len(cache),
        "min1000": len(all_min),
        "below_1000": len(below),
        "unknown": len(unknown),
        "by_year": {str(y): len(by_year.get(y, [])) for y in sorted(years)},
        "finishedAt": datetime.now(timezone.utc).isoformat(),
    }
    (base / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


async def main() -> None:
    args = parse_args()
    base = Path(args.output_dir)
    years = set(range(args.start_year, args.end_year + 1))
    (base / COUNTRY_DIR).mkdir(parents=True, exist_ok=True)

    pool = await build_pool(args)
    all_channels: dict[str, str] = {}
    all_channels.update(load_discovered(base))
    all_channels.update(load_ids_from_year_files(base))
    log(f"[init] known_ids={len(all_channels)}")

    cache = load_enrich_cache(base)
    log(f"[init] enriched_cache={len(cache)}")

    meta = ClientMeta()
    sem = asyncio.Semaphore(args.concurrency)

    # Phase search
    if not args.skip_search and not args.enrich_only:
        queries = default_queries(args.extra_bigrams)
        log(f"[search] queries={len(queries)} pages={args.max_pages_per_query}")
        async with await make_client(None) as client:
            await meta.refresh(client, force=True)
            for i, q in enumerate(queries, 1):
                found = await search_channels(client, meta, q, args.max_pages_per_query, sem, args.delay)
                before = len(all_channels)
                all_channels.update(found)
                log(f"[search] [{i}/{len(queries)}] q={q!r} +{len(all_channels)-before} unique={len(all_channels)}")
                if i % 15 == 0:
                    save_discovered(base, all_channels)
        save_discovered(base, all_channels)
    else:
        log("[search] skipped")

    # Phase enrich — only ids never successfully fetched.
    # year-only (subs hidden by YouTube) is treated as done; re-fetching won't help.
    todo = [
        (cid, title)
        for cid, title in all_channels.items()
        if cid not in cache
        or (cache[cid].subscribers is None and cache[cid].year is None)
    ]
    year_only = sum(
        1
        for cid in all_channels
        if cid in cache and cache[cid].year is not None and cache[cid].subscribers is None
    )
    log(
        f"[enrich] todo={len(todo)} year_only_skip={year_only} "
        f"cached_full={len(all_channels)-len(todo)-year_only} "
        f"min_subs={args.min_subs} conc={args.concurrency} delay={args.delay}"
    )

    done = ok1k = below = unknown = 0
    batch = max(48, int(args.batch_size))
    log(f"[enrich] starting workers conc={args.concurrency} batch={batch}")

    async with await make_client(None, timeout=9.0) as shared:
        for i in range(0, len(todo), batch):
            if i > 0 and i % (batch * 10) == 0 and len(pool) < 2 and args.fetch_free_proxies:
                log("[proxy] low, refill...")
                try:
                    cands = await asyncio.wait_for(fetch_free_proxies(8), timeout=10)
                    sem_p = asyncio.Semaphore(20)

                    async def try_add(p: str) -> None:
                        async with sem_p:
                            if not await probe_proxy(p):
                                return
                            key = p if "://" in p else f"http://{p}"
                            async with pool._lock:
                                if key not in pool.proxies and key not in pool.bad:
                                    pool.proxies.append(key)

                    await asyncio.wait_for(
                        asyncio.gather(*[try_add(p) for p in cands[:16]], return_exceptions=True),
                        timeout=12,
                    )
                except Exception as e:
                    log(f"[proxy] refill skip: {type(e).__name__}")
                log(f"[proxy] alive={len(pool)}")

            chunk = todo[i : i + batch]
            tasks = [
                asyncio.create_task(
                    enrich_channel(cid, title, pool, sem, args.delay, cache, shared)
                )
                for cid, title in chunk
            ]
            for fut in asyncio.as_completed(tasks):
                try:
                    info = await fut
                except Exception:
                    unknown += 1
                    done += 1
                    continue
                done += 1
                if info.subscribers is None or info.year is None:
                    unknown += 1
                elif info.subscribers >= args.min_subs:
                    ok1k += 1
                else:
                    below += 1
                if done % 80 == 0:
                    log(
                        f"[enrich] {done}/{len(todo)} min1000={ok1k} below={below} "
                        f"unknown={unknown} proxies={len(pool)}"
                    )
                if done % 400 == 0:
                    save_enrich_cache(base, cache)
                    summary = write_outputs(base, cache, args.min_subs, years)
                    log(
                        f"[flush] min1000={summary['min1000']} "
                        f"below={summary['below_1000']} unknown={summary['unknown']}"
                    )
            log(
                f"[enrich] {done}/{len(todo)} min1000={ok1k} below={below} "
                f"unknown={unknown} proxies={len(pool)}"
            )

    save_discovered(base, all_channels)
    save_enrich_cache(base, cache)
    summary = write_outputs(base, cache, args.min_subs, years)
    log(f"[done] {json.dumps(summary, ensure_ascii=False)}")


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
