"""OSINT sonuçlarından AI için yapılandırılmış bağlam üretir."""

import json


def _collect_errors(data: dict) -> list[str]:
  errors = []
  for key in ("platforms", "registrations", "breaches", "email_intel", "username_platforms"):
    section = data.get(key) or {}
    if section.get("error"):
      errors.append(f"{key}: {section['error']}")
    stats = section.get("stats") or {}
    if stats.get("modules_errored", 0) > 0:
      source = section.get("source", key)
      errors.append(
        f"{source}: {stats['modules_errored']}/{stats.get('modules_total', '?')} modül hata verdi"
      )
    for sample in stats.get("error_samples", []):
      errors.append(f"tarama hatası: {sample}")
  if data.get("error"):
    errors.append(str(data["error"]))
  return errors


def _collect_scan_coverage(data: dict) -> dict:
  regs = data.get("registrations") or {}
  breaches = data.get("breaches") or {}
  platforms = data.get("platforms") or data.get("username_platforms") or {}
  intel = data.get("email_intel") or {}
  stats = regs.get("stats") or {}

  return {
    "email_scan_found": regs.get("count", 0),
    "email_scan_checked": regs.get("total_checked", 0),
    "email_scan_errors": stats.get("modules_errored", 0),
    "email_scan_source": regs.get("source", "user-scanner"),
    "sherlock_found": platforms.get("found_count", 0),
    "sherlock_checked": platforms.get("total_checked", 0),
    "platform_sources": platforms.get("sources", {}),
    "breach_count": breaches.get("count", 0),
    "paste_count": breaches.get("paste_count", 0),
    "gravatar_found": (intel.get("gravatar") or {}).get("exists", False),
    "linked_accounts": len(intel.get("linked_accounts", [])),
    "disposable_email": intel.get("is_disposable", False),
  }


def _build_timeline(data: dict) -> list[dict]:
  events = []
  for b in (data.get("breaches") or {}).get("breaches", []):
    if b.get("date"):
      events.append({"year": str(b["date"]), "event": f"Veri sızıntısı: {b.get('name')}", "type": "breach"})
  for p in (data.get("breaches") or {}).get("pastes", []):
    if p.get("date"):
      events.append({"year": str(p["date"])[:4], "event": f"Paste sızıntısı: {p.get('source')}", "type": "paste"})
  yearly = ((data.get("breaches") or {}).get("metrics") or {}).get("yearly_breakdown", [])
  for item in yearly:
    if isinstance(item, (list, tuple)) and len(item) >= 2:
      events.append({"year": str(item[0]), "event": f"{item[1]} sızıntı kaydı", "type": "metric"})
  events.sort(key=lambda x: x.get("year", ""), reverse=True)
  return events[:20]


def build_analysis_context(data: dict, scan_meta: dict | None = None) -> dict:
  breaches = data.get("breaches") or {}
  regs = data.get("registrations") or {}
  platforms = data.get("platforms") or data.get("username_platforms") or {}
  intel = data.get("email_intel") or {}

  password_in_breach = breaches.get("has_password_exposure", False)
  recovery_hints = [
    s.get("emailrecovery") for s in regs.get("registered_services", []) if s.get("emailrecovery")
  ]
  phone_hints = [
    s.get("phoneNumber") for s in regs.get("registered_services", []) if s.get("phoneNumber")
  ]

  critical_signals = []
  if password_in_breach:
    critical_signals.append("Şifreler veri sızıntılarında açığa çıkmış")
  if breaches.get("paste_count", 0) > 0:
    critical_signals.append(f"{breaches['paste_count']} paste/platform sızıntısı tespit edildi")
  if recovery_hints:
    critical_signals.append(f"{len(recovery_hints)} serviste kurtarma e-postası ipucu sızdı")
  if phone_hints:
    critical_signals.append(f"{len(phone_hints)} serviste telefon numarası ipucu sızdı")
  if intel.get("is_disposable"):
    critical_signals.append("Geçici/tek kullanımlık e-posta domaini")
  if (intel.get("gravatar") or {}).get("exists"):
    critical_signals.append("Gravatar profili aktif — kimlik bilgisi bağlantısı mevcut")

  return {
    "target": data.get("target"),
    "target_type": data.get("target_type"),
    "scanned_at": data.get("scanned_at"),
    "scan_meta": scan_meta or {},
    "coverage": _collect_scan_coverage(data),
    "errors": _collect_errors(data),
    "critical_signals": critical_signals,
    "timeline": _build_timeline(data),
    "exposed_data_types": breaches.get("exposed_data_types", []),
    "breach_metrics": breaches.get("metrics", {}),
    "gravatar_profile": intel.get("gravatar"),
    "dns_info": intel.get("dns"),
    "linked_accounts": intel.get("linked_accounts", []),
    "top_breaches": (breaches.get("breaches") or [])[:15],
    "top_registrations": (regs.get("registered_services") or [])[:25],
    "top_platforms": (platforms.get("found") or [])[:25],
    "email_scan_stats": regs.get("stats", {}),
    "raw_summary": {
      "registration_count": regs.get("count", 0),
      "breach_count": breaches.get("count", 0),
      "platform_count": platforms.get("found_count", 0),
    },
  }


def context_to_prompt_text(context: dict) -> str:
  return json.dumps(context, ensure_ascii=False, indent=2, default=str)
