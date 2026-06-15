import httpx

XON_API = "https://api.xposedornot.com/v1"


def _parse_breach_details(data: dict) -> list[dict]:
  exposed = data.get("ExposedBreaches") or {}
  details = exposed.get("breaches_details") or []
  breaches = []
  for b in details:
    xposed_data = b.get("xposed_data", "")
    data_classes = [d.strip() for d in xposed_data.split(";") if d.strip()]
    breaches.append(
      {
        "name": b.get("breach"),
        "date": b.get("xposed_date"),
        "data_classes": data_classes,
        "domain": b.get("domain"),
        "records": b.get("xposed_records"),
        "industry": b.get("industry"),
        "password_risk": b.get("password_risk"),
        "verified": b.get("verified"),
        "details": b.get("details"),
      }
    )
  return breaches


def _parse_pastes(data: dict) -> list[dict]:
  exposed = data.get("ExposedPastes")
  if not exposed:
    return []
  paste_list = exposed if isinstance(exposed, list) else exposed.get("pastes", [])
  if not paste_list:
    summary = data.get("PastesSummary") or {}
    if summary.get("cnt", 0) > 0:
      return [{"source": summary.get("domain", "paste"), "count": summary["cnt"]}]
    return []

  pastes = []
  for p in paste_list:
    if isinstance(p, dict):
      pastes.append({
        "source": p.get("site") or p.get("domain") or "paste",
        "date": p.get("date") or p.get("tmpstmp"),
        "title": p.get("title"),
      })
  return pastes


def _merge_breach_names(existing: list[dict], names: list[str]) -> list[dict]:
  known = {b["name"].lower() for b in existing if b.get("name")}
  merged = list(existing)
  for name in names:
    if name and name.lower() not in known:
      merged.append({"name": name, "date": None, "data_classes": [], "source": "check-email"})
      known.add(name.lower())
  return merged


def _check_email_extra(email: str, headers: dict) -> list[str]:
  try:
    with httpx.Client(timeout=15.0) as client:
      resp = client.get(f"{XON_API}/check-email/{email}", params={"details": "true"}, headers=headers)
    if resp.status_code != 200:
      return []
    data = resp.json()
    if data.get("Error") or data.get("status") != "success":
      return []
    raw = data.get("breaches", [])
    if raw and isinstance(raw[0], list):
      return raw[0]
    return raw if isinstance(raw, list) else []
  except Exception:
    return []


def run_breach_check(email: str) -> dict:
  """XposedOrNot — derin sızıntı + paste + analytics analizi."""
  headers = {"User-Agent": "Tunel-OSINT/1.0"}

  try:
    with httpx.Client(timeout=25.0) as client:
      analytics_resp = client.get(
        f"{XON_API}/breach-analytics",
        params={"email": email},
        headers=headers,
      )

    if analytics_resp.status_code == 429:
      return {
        "error": "Sızıntı API rate limit aşıldı (günde 100 istek)",
        "breached": False, "breaches": [], "pastes": [], "source": "xposedornot",
      }

    breaches = []
    pastes = []
    metrics = {}
    exposed_data_types = []

    if analytics_resp.status_code == 200:
      data = analytics_resp.json()
      breaches = _parse_breach_details(data)
      pastes = _parse_pastes(data)

      bm = data.get("BreachMetrics") or {}
      risk = bm.get("risk")
      metrics = {
        "risk_score": risk[0].get("risk_score") if risk else None,
        "risk_label": risk[0].get("risk_label") if risk else None,
        "password_strength": bm.get("passwords_strength"),
        "yearly_breakdown": bm.get("yearly", []),
      }

      xposed = bm.get("xposed_data") or data.get("xposed_data")
      if xposed:
        exposed_data_types = _extract_exposed_types(xposed)

      extra_names = _check_email_extra(email, headers)
      breaches = _merge_breach_names(breaches, extra_names)

    elif analytics_resp.status_code == 404:
      extra_names = _check_email_extra(email, headers)
      breaches = [{"name": n, "date": None, "data_classes": []} for n in extra_names]
    else:
      extra_names = _check_email_extra(email, headers)
      breaches = [{"name": n, "date": None, "data_classes": []} for n in extra_names]

    has_passwords = any(
      any("password" in dc.lower() for dc in b.get("data_classes", []))
      for b in breaches
    )

    return {
      "breached": len(breaches) > 0,
      "count": len(breaches),
      "breaches": breaches,
      "pastes": pastes,
      "paste_count": len(pastes),
      "metrics": metrics,
      "exposed_data_types": exposed_data_types,
      "has_password_exposure": has_passwords,
      "source": "xposedornot",
    }

  except httpx.HTTPStatusError as e:
    return {
      "error": f"Sızıntı API HTTP hatası: {e.response.status_code}",
      "breached": False, "breaches": [], "pastes": [], "source": "xposedornot",
    }
  except Exception as e:
    return {"error": str(e), "breached": False, "breaches": [], "pastes": [], "source": "xposedornot"}


def _extract_exposed_types(xposed) -> list[str]:
  types = []

  def walk(node):
    if isinstance(node, dict):
      if node.get("name", "").startswith("data_"):
        types.append(node["name"].replace("data_", "").replace("_", " "))
      for v in node.values():
        walk(v)
    elif isinstance(node, list):
      for item in node:
        walk(item)

  walk(xposed)
  return list(dict.fromkeys(types))
