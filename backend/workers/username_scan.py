from concurrent.futures import ThreadPoolExecutor

from config import settings
from workers.sherlock import run_sherlock
from workers.user_scanner_username import run_user_scanner_username
from workers.whatsmyname import run_whatsmyname


def _merge_platform_results(sources: list[tuple[str, dict]]) -> dict:
  merged = []
  seen_urls: set[str] = set()
  seen_names: set[str] = set()
  total_checked = 0
  source_stats = {}
  errors = []

  for source_name, data in sources:
    if data.get("error"):
      errors.append(f"{source_name}: {data['error']}")
    if data.get("warning"):
      errors.append(f"{source_name}: {data['warning']}")

    source_stats[source_name] = {
      "found": data.get("found_count", 0),
      "checked": data.get("total_checked", 0),
      "error": data.get("error"),
    }
    total_checked += data.get("total_checked", 0)

    for item in data.get("found", []):
      platform = item.get("platform") or item.get("name", "unknown")
      url = item.get("url", "")
      name_key = platform.lower()
      dedupe = url.lower() if url else name_key

      if dedupe in seen_urls or (not url and name_key in seen_names):
        continue
      if url:
        seen_urls.add(dedupe)
      seen_names.add(name_key)

      merged.append({
        "platform": platform,
        "url": url,
        "category": item.get("category"),
        "source": item.get("source", source_name),
      })

  return {
    "found": merged,
    "found_count": len(merged),
    "total_checked": total_checked,
    "sources": source_stats,
    "errors": errors,
  }


def run_username_scan(username: str, timeout: int | None = None) -> dict:
  """Sherlock + WhatsMyName + User-Scanner — bir motor çökse diğerleri devam eder."""
  timeout = timeout or settings.engine_timeout_seconds
  jobs = {
    "sherlock": run_sherlock,
    "whatsmyname": run_whatsmyname,
    "user-scanner": run_user_scanner_username,
  }

  results = {}
  with ThreadPoolExecutor(max_workers=3) as executor:
    futures = {name: executor.submit(fn, username) for name, fn in jobs.items()}
    for name, future in futures.items():
      try:
        results[name] = future.result(timeout=timeout)
      except Exception as e:
        results[name] = {
          "error": f"Zaman aşımı veya hata: {e}",
          "found": [],
          "found_count": 0,
          "source": name,
        }

  merged = _merge_platform_results(list(results.items()))
  merged["engines"] = list(jobs.keys())
  return merged
