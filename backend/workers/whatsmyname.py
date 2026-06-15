import asyncio
import json
import time
from pathlib import Path

import httpx

from config import settings
from workers.http_utils import merge_headers, request_with_retry

WMN_URL = "https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json"
CACHE_FILE = Path(__file__).resolve().parent.parent / "data" / "wmn-data.json"
CACHE_TTL = 86400
SKIP_CATEGORIES = {"xx NSFW xx", "archived"}


def _load_sites() -> list[dict]:
  now = time.time()
  if CACHE_FILE.exists():
    age = now - CACHE_FILE.stat().st_mtime
    if age < CACHE_TTL:
      data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
      return _filter_sites(data.get("sites", []))

  with httpx.Client(timeout=30.0, headers=merge_headers()) as client:
    resp = client.get(WMN_URL)
    resp.raise_for_status()
    data = resp.json()

  CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
  CACHE_FILE.write_text(json.dumps(data), encoding="utf-8")
  return _filter_sites(data.get("sites", []))


def _filter_sites(sites: list[dict]) -> list[dict]:
  filtered = []
  for site in sites:
    if not site.get("uri_check") or "{account}" not in site["uri_check"]:
      continue
    if site.get("cat") in SKIP_CATEGORIES and not settings.wmn_include_nsfw:
      continue
    if site.get("disabled"):
      continue
  # POST-only siteler şimdilik atlanır (GET destekli olanlar daha güvenilir)
    if site.get("post") or site.get("uri_probe"):
      continue
    filtered.append(site)
  return filtered


def _is_found(resp: httpx.Response, body: str, site: dict) -> bool:
  m_string = site.get("m_string")
  m_code = site.get("m_code")
  e_string = site.get("e_string")
  e_code = site.get("e_code")

  if m_string and m_string in body:
    return False
  if m_code is not None and resp.status_code == m_code:
    return False

  if e_string and e_string in body:
    if e_code is None or resp.status_code == e_code:
      return True

  if e_code is not None and resp.status_code == e_code and not m_string:
    return True

  return False


async def _check_site(client: httpx.AsyncClient, site: dict, username: str) -> dict | None:
  url = site["uri_check"].replace("{account}", username)
  headers = merge_headers(site.get("headers"))

  resp = await request_with_retry(
    client, "GET", url,
    headers=headers,
    follow_redirects=True,
    retries=settings.http_retries,
  )
  if resp is None:
    return None

  if _is_found(resp, resp.text, site):
    return {
      "platform": site.get("name", "unknown"),
      "url": str(resp.url),
      "category": site.get("cat"),
      "source": "whatsmyname",
    }
  return None


async def _run_wmn_async(username: str) -> dict:
  sites = _load_sites()
  found = []
  errors = 0
  sem = asyncio.Semaphore(settings.wmn_concurrency)

  timeout = httpx.Timeout(settings.wmn_request_timeout, connect=10.0)
  async with httpx.AsyncClient(timeout=timeout, headers=merge_headers()) as client:

    async def bounded_check(site):
      nonlocal errors
      async with sem:
        try:
          result = await _check_site(client, site, username)
          return result
        except Exception:
          errors += 1
          return None

    results = await asyncio.gather(*[bounded_check(s) for s in sites])

  for r in results:
    if r:
      found.append(r)

  return {
    "found": found,
    "found_count": len(found),
    "total_checked": len(sites),
    "source": "whatsmyname",
    "stats": {"errors": errors, "sites_total": len(sites)},
  }


def run_whatsmyname(username: str) -> dict:
  """WhatsMyName — 700+ platform, ücretsiz JSON veritabanı."""
  try:
    return asyncio.run(_run_wmn_async(username))
  except Exception as e:
    return {"error": str(e), "found": [], "found_count": 0, "source": "whatsmyname"}
