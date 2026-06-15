import asyncio

from user_scanner.core import engine
from user_scanner.core.result import Status


async def _run_username_scan_async(username: str) -> dict:
  results = await engine.check_all(username, is_email=False)

  found = []
  errors = 0
  for r in results:
    if r.is_found():
      found.append({
        "platform": r.site_name,
        "url": r.url,
        "category": r.category,
        "source": "user-scanner",
      })
    elif r.status == Status.ERROR:
      errors += 1

  return {
    "found": found,
    "found_count": len(found),
    "total_checked": len(results),
    "source": "user-scanner",
    "stats": {"modules_errored": errors, "modules_total": len(results)},
  }


def run_user_scanner_username(username: str) -> dict:
  """User-Scanner kullanıcı adı modu — 100+ platform."""
  try:
    return asyncio.run(_run_username_scan_async(username))
  except Exception as e:
    return {"error": str(e), "found": [], "found_count": 0, "source": "user-scanner"}
