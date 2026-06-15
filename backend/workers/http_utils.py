import asyncio
from typing import Callable

import httpx

BROWSER_HEADERS = {
  "User-Agent": (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
  ),
  "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
  "Accept-Language": "en-US,en;q=0.9,tr;q=0.8",
}


async def request_with_retry(
  client: httpx.AsyncClient,
  method: str,
  url: str,
  *,
  retries: int = 2,
  **kwargs,
) -> httpx.Response | None:
  last_error = None
  for attempt in range(retries + 1):
    try:
      if method.upper() == "POST":
        return await client.post(url, **kwargs)
      return await client.get(url, **kwargs)
    except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as e:
      last_error = e
      if attempt < retries:
        await asyncio.sleep(0.5 * (attempt + 1))
  return None


def merge_headers(extra: dict | None = None) -> dict:
  headers = dict(BROWSER_HEADERS)
  if extra:
    headers.update(extra)
  return headers
