import hashlib
import re

import httpx

DISPOSABLE_DOMAINS = {
  "mailinator.com", "guerrillamail.com", "tempmail.com", "10minutemail.com",
  "throwaway.email", "yopmail.com", "sharklasers.com", "trashmail.com",
}

PROVIDER_HINTS = {
  "google.com": "Google Gmail",
  "googlemail.com": "Google Gmail",
  "outlook.com": "Microsoft Outlook",
  "hotmail.com": "Microsoft Outlook",
  "live.com": "Microsoft Outlook",
  "yahoo.com": "Yahoo Mail",
  "icloud.com": "Apple iCloud",
  "protonmail.com": "ProtonMail",
  "proton.me": "ProtonMail",
}


def _parse_email(email: str) -> tuple[str, str]:
  parts = email.strip().lower().split("@", 1)
  if len(parts) != 2:
    return "", ""
  return parts[0], parts[1]


def _gravatar_lookup(email: str) -> dict:
  normalized = email.strip().lower().encode("utf-8")
  email_hash = hashlib.md5(normalized).hexdigest()
  try:
    with httpx.Client(timeout=10.0) as client:
      resp = client.get(f"https://www.gravatar.com/{email_hash}.json")
    if resp.status_code == 404:
      return {"exists": False}
    if resp.status_code != 200:
      return {"exists": False, "error": f"HTTP {resp.status_code}"}
    data = resp.json()
    entry = data.get("entry", [{}])[0]
    return {
      "exists": True,
      "display_name": entry.get("displayName"),
      "profile_url": entry.get("profileUrl"),
      "username": entry.get("preferredUsername"),
      "photos": [p.get("value") for p in entry.get("photos", []) if p.get("value")],
      "accounts": [
        {"domain": a.get("domain"), "username": a.get("username"), "url": a.get("url")}
        for a in entry.get("accounts", [])
      ],
    }
  except Exception as e:
    return {"exists": False, "error": str(e)}


def _dns_lookup(domain: str) -> dict:
  result = {"domain": domain, "mx_records": [], "mail_provider": PROVIDER_HINTS.get(domain)}
  try:
    with httpx.Client(timeout=10.0) as client:
      mx_resp = client.get("https://dns.google/resolve", params={"name": domain, "type": "MX"})
      if mx_resp.status_code == 200:
        answers = mx_resp.json().get("Answer", [])
        for ans in answers:
          data = ans.get("data", "")
          host = data.split()[-1].rstrip(".") if data else ""
          if host:
            result["mx_records"].append(host)
            for hint_domain, provider in PROVIDER_HINTS.items():
              if hint_domain in host:
                result["mail_provider"] = provider
                break

      txt_resp = client.get("https://dns.google/resolve", params={"name": domain, "type": "TXT"})
      if txt_resp.status_code == 200:
        txts = [a.get("data", "").strip('"') for a in txt_resp.json().get("Answer", [])]
        result["spf_record"] = next((t for t in txts if t.startswith("v=spf1")), None)
        result["dmarc_available"] = any("_dmarc" in t for t in txts)
  except Exception as e:
    result["error"] = str(e)
  return result


def run_email_intel(email: str) -> dict:
  """E-posta metadata: Gravatar, DNS/MX, domain analizi."""
  local, domain = _parse_email(email)
  if not domain:
    return {"error": "Geçersiz e-posta formatı"}

  gravatar = _gravatar_lookup(email)
  dns = _dns_lookup(domain)

  linked_accounts = gravatar.get("accounts", []) if gravatar.get("exists") else []

  return {
    "local_part": local,
    "domain": domain,
    "is_disposable": domain in DISPOSABLE_DOMAINS,
    "gravatar": gravatar,
    "dns": dns,
    "linked_accounts": linked_accounts,
    "derived_username": local if _is_valid_derived_username(local) else None,
    "pivot_links": {
      "google": f"https://www.google.com/search?q=%22{email}%22",
      "github": f"https://github.com/search?q={email}&type=users",
      "hibp_web": f"https://haveibeenpwned.com/account/{email}",
      "xposedornot": f"https://xposedornot.com/?q={email}",
    },
  }


def _is_valid_derived_username(local: str) -> bool:
  if len(local) < 3 or len(local) > 30:
    return False
  generic = {"admin", "info", "support", "contact", "mail", "hello", "noreply", "sales", "help"}
  if local in generic:
    return False
  return bool(re.match(r"^[a-zA-Z0-9._-]+$", local))
