import io
import json
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def generate_pdf_report(target: str, target_type: str, data: dict) -> bytes:
  buffer = io.BytesIO()
  doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2 * cm, leftMargin=2 * cm)
  styles = getSampleStyleSheet()
  title_style = ParagraphStyle("Title", parent=styles["Heading1"], fontSize=18, spaceAfter=12)
  heading_style = ParagraphStyle("Heading", parent=styles["Heading2"], fontSize=13, spaceAfter=8)
  body_style = styles["Normal"]

  story = []
  story.append(Paragraph("Tunel — OSINT Raporu", title_style))
  story.append(Paragraph(f"Hedef: <b>{target}</b> ({target_type})", body_style))
  story.append(Paragraph(f"Tarih: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", body_style))
  story.append(Spacer(1, 0.5 * cm))

  ai = data.get("ai_analysis", {})
  story.append(Paragraph("AI Analizi", heading_style))
  story.append(Paragraph(f"Risk Skoru: <b>{ai.get('risk_score', 'N/A')}/100</b>", body_style))
  story.append(Paragraph(f"Risk Seviyesi: <b>{ai.get('risk_level', 'N/A')}</b>", body_style))
  story.append(Paragraph(ai.get("summary", ""), body_style))
  story.append(Spacer(1, 0.3 * cm))

  if ai.get("recommendations"):
    story.append(Paragraph("Öneriler:", body_style))
    for rec in ai["recommendations"]:
      story.append(Paragraph(f"• {rec}", body_style))
  story.append(Spacer(1, 0.5 * cm))

  if data.get("platforms"):
    platforms = data["platforms"]
    story.append(Paragraph(f"Platform Taraması ({platforms.get('found_count', 0)} bulundu)", heading_style))
    rows = [["Platform", "URL"]]
    for item in platforms.get("found", [])[:30]:
      rows.append([item.get("platform", ""), item.get("url", "")])
    if len(rows) > 1:
      table = Table(rows, colWidths=[5 * cm, 12 * cm])
      table.setStyle(
        TableStyle(
          [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
          ]
        )
      )
      story.append(table)
    story.append(Spacer(1, 0.5 * cm))

  if data.get("breaches"):
    breaches = data["breaches"]
    story.append(Paragraph(f"Veri Sızıntıları ({breaches.get('count', 0)})", heading_style))
    for b in breaches.get("breaches", [])[:20]:
      story.append(
        Paragraph(
          f"• <b>{b.get('name')}</b> — {b.get('date')} — {', '.join(b.get('data_classes', []))}",
          body_style,
        )
      )
    story.append(Spacer(1, 0.5 * cm))

  if data.get("registrations"):
    regs = data["registrations"]
    story.append(Paragraph(f"Kayıtlı Servisler ({regs.get('count', 0)})", heading_style))
    for s in regs.get("registered_services", [])[:20]:
      story.append(Paragraph(f"• {s.get('name')}", body_style))

  doc.build(story)
  buffer.seek(0)
  return buffer.read()
