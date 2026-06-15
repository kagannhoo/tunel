import json
import re

from ai.context_builder import build_analysis_context, context_to_prompt_text
from config import settings


def _normalize_recommendations(recs) -> list:
  if not recs:
    return []
  normalized = []
  for r in recs:
    if isinstance(r, str):
      normalized.append({"priority": "orta", "action": r})
    elif isinstance(r, dict):
      normalized.append({
        "priority": r.get("priority", "orta"),
        "action": r.get("action", r.get("text", str(r))),
      })
  return normalized


def _heuristic_analysis(data: dict, context: dict) -> dict:
  coverage = context["coverage"]
  score = 0

  score += min(coverage.get("email_scan_found", 0) * 2, 15)
  score += min(coverage.get("sherlock_found", 0) * 2, 25)
  score += min(coverage.get("breach_count", 0) * 8, 35)
  score += min(coverage.get("paste_count", 0) * 10, 15)
  if context.get("critical_signals"):
    score += min(len(context["critical_signals"]) * 5, 20)
  score = min(score, 100)

  if score >= 75:
    level = "kritik"
  elif score >= 50:
    level = "yüksek"
  elif score >= 25:
    level = "orta"
  else:
    level = "düşük"

  risk_factors = []
  for sig in context.get("critical_signals", []):
    risk_factors.append({"title": sig, "severity": "yüksek", "detail": "Otomatik tespit"})

  if coverage.get("email_scan_errors", 0) > 10:
    risk_factors.append({
      "title": "E-posta tarama hataları",
      "severity": "orta",
      "detail": f"{coverage['email_scan_errors']} servis kontrol edilemedi — sonuçlar eksik olabilir",
    })

  errors = context.get("errors", [])
  summary_parts = [
    f"{coverage.get('email_scan_found', 0)} serviste e-posta kaydı,",
    f"{coverage.get('sherlock_found', 0)} platformda kullanıcı adı izi,",
    f"{coverage.get('breach_count', 0)} veri sızıntısı bulundu.",
  ]

  return {
    "risk_score": score,
    "risk_level": level,
    "summary": " ".join(summary_parts),
    "executive_summary": (
      f"Dijital ayak izi {level} risk seviyesinde. "
      + ("Kritik sinyaller: " + "; ".join(context.get("critical_signals", [])[:3]) if context.get("critical_signals") else "Belirgin kritik sinyal yok.")
    ),
    "risk_factors": risk_factors,
    "critical_findings": context.get("critical_signals", []),
    "attack_surface": (
      f"Toplam {coverage.get('email_scan_found', 0) + coverage.get('sherlock_found', 0)} aktif dijital iz; "
      f"{coverage.get('breach_count', 0)} bilinen sızıntı kaydı."
    ),
    "recommendations": _normalize_recommendations([
      "Sızdığı bilinen tüm platformlarda şifreleri derhal değiştirin.",
      "İki faktörlü kimlik doğrulamayı tüm kritik hesaplarda etkinleştirin.",
      "Kullanılmayan hesapları kapatın ve Gravatar/sosyal bağlantıları gözden geçirin.",
    ]),
    "errors_and_gaps": errors,
    "timeline": context.get("timeline", [])[:10],
    "coverage": coverage,
    "source": "heuristic",
  }


def _parse_llm_json(text: str) -> dict:
  text = text.strip()
  fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
  if fence:
    text = fence.group(1).strip()
  return json.loads(text)


def analyze_results(data: dict, scan_meta: dict | None = None) -> dict:
  context = build_analysis_context(data, scan_meta)
  context_text = context_to_prompt_text(context)

  if not settings.anthropic_api_key:
    return _heuristic_analysis(data, context)

  try:
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    prompt = f"""Sen kıdemli bir OSINT ve siber güvenlik analistsin. Tunel tarama sonuçlarını derinlemesine analiz et.

GÖREV:
- Somut bulgulara dayan, genel laflardan kaçın
- Hataları ve eksik taramaları açıkça belirt (errors_and_gaps)
- Şifre sızıntısı, kurtarma ipuçları, paste'ler, Gravatar bağlantıları gibi kritik riskleri vurgula
- Risk skorunu bulguların ciddiyetine göre kalibre et (0-100)
- Türkçe yaz

TARAMA BAĞLAMI:
{context_text}

SADECE JSON döndür (başka metin yok):
{{
  "risk_score": <0-100>,
  "risk_level": "düşük" | "orta" | "yüksek" | "kritik",
  "summary": "<3-4 cümle teknik özet>",
  "executive_summary": "<yöneticiye 1-2 cümle>",
  "attack_surface": "<saldırı yüzeyi analizi: kaç iz, hangi kanallar>",
  "critical_findings": ["<acil dikkat gerektiren bulgu>", ...],
  "risk_factors": [
    {{"title": "<başlık>", "severity": "düşük|orta|yüksek|kritik", "detail": "<açıklama>"}}
  ],
  "recommendations": [
    {{"priority": "yüksek|orta|düşük", "action": "<somut aksiyon>"}}
  ],
  "errors_and_gaps": ["<tarama hatası veya eksik kapsam>", ...],
  "timeline": [
    {{"year": "<yıl>", "event": "<olay>", "type": "breach|paste|other"}}
  ]
}}"""

    message = client.messages.create(
      model="claude-sonnet-4-20250514",
      max_tokens=2000,
      messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text
    result = _parse_llm_json(raw)
    result["recommendations"] = _normalize_recommendations(result.get("recommendations", []))
    result["coverage"] = context["coverage"]
    result["source"] = "llm"
    if not result.get("errors_and_gaps"):
      result["errors_and_gaps"] = context.get("errors", [])
    return result

  except Exception as e:
    fallback = _heuristic_analysis(data, context)
    fallback["llm_error"] = str(e)
    return fallback
