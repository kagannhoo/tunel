import asyncio

from user_scanner.core import engine
from user_scanner.core.result import Status


async def _run_email_scan_async(email: str) -> dict:
  results = await engine.check_all(email, is_email=True)

  registered = []
  errors = []

  for r in results:
    if r.is_found():
      extra = r.extra or {}
      registered.append(
        {
          "name": r.site_name,
          "category": r.category,
          "url": r.url,
          "emailrecovery": extra.get("recovery_email") or extra.get("emailrecovery"),
          "phoneNumber": extra.get("phone") or extra.get("phonenumber") or extra.get("phone_number"),
          "extra": extra,
        }
      )
    elif r.status == Status.ERROR:
      errors.append({"site": r.site_name, "reason": r.get_reason()})

  not_found = sum(1 for r in results if r.status == Status.AVAILABLE)
  skipped = sum(1 for r in results if r.status == Status.SKIPPED)

  return {
    "email": email,
    "registered_services": registered,
    "count": len(registered),
    "total_checked": len(results),
    "source": "user-scanner",
    "stats": {
      "modules_total": len(results),
      "modules_found": len(registered),
      "modules_errored": len(errors),
      "modules_not_found": not_found,
      "modules_skipped": skipped,
      "error_samples": list(dict.fromkeys(e["reason"] for e in errors if e.get("reason")))[:5],
    },
  }


def run_email_scan(email: str) -> dict:
  """User-Scanner ile e-posta kayıt taraması (Holehe yerine)."""
  try:
    return asyncio.run(_run_email_scan_async(email))
  except Exception as e:
    return {
      "error": str(e),
      "registered_services": [],
      "count": 0,
      "source": "user-scanner",
      "stats": {},
    }
