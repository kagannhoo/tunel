# Tunel // OSINT Intelligence Terminal

[![License: MIT](https://img.shields.io/badge/License-MIT-00e676.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61dafb.svg)](https://react.dev)

```
~/osint $ tunel --scan target@email.com
```

Kullanıcı adı veya e-posta ile **çok katmanlı OSINT taraması** yapan, **AI risk analizi** üreten ve **PDF rapor** sunan açık kaynak terminal panosu.

> ⚠️ **Etik kullanım:** Yalnızca kendi hesaplarınızı veya yazılı izniniz olan hedefleri tarayın.

---

## Özellikler

- **3 motorlu platform taraması** — Sherlock · WhatsMyName · User-Scanner
- **E-posta taraması** — User-Scanner + XposedOrNot + Gravatar/DNS
- **AI risk analizi** — Claude (opsiyonel) veya heuristic fallback
- **PDF rapor** · **Rate limiting** · **Docker Compose**

---

## Mimari

```
React UI (:3000)
      ↓
FastAPI (:8000) → Celery Worker
      ↓                ↓
  PostgreSQL         Redis
```

---

## Kurulum

```bash
git clone https://github.com/kagannhoo/tunel.git
cd tunel
cp .env.example .env
docker compose up --build
```

| Servis | URL |
|--------|-----|
| Terminal UI | http://localhost:3000 |
| API | http://localhost:8000 |
| Docs | http://localhost:8000/docs |

---

## OSINT Stack (ücretsiz)

| Katman | Araç |
|--------|------|
| Platform | Sherlock + WhatsMyName + User-Scanner |
| E-posta kayıt | User-Scanner |
| Sızıntı | XposedOrNot |
| Intel | Gravatar + DNS |
| AI | Anthropic Claude (opsiyonel) |

---

## Geliştirme

```bash
pip install -r requirements.txt
cd backend && uvicorn main:app --reload
celery -A tasks worker --loglevel=info
cd frontend && npm install && npm run dev
```

---

## Kaynakça

Bu proje aşağıdaki açık kaynak araçlar ve servisler üzerine inşa edilmiştir:

### OSINT Araçları

| Araç | Yazar / Kurum | Bağlantı |
|------|---------------|----------|
| **Sherlock** | Sherlock Project | https://github.com/sherlock-project/sherlock |
| **WhatsMyName** | Micah Hoffman (WebBreacher) | https://github.com/WebBreacher/WhatsMyName |
| **User-Scanner** | kaifcodec | https://github.com/kaifcodec/user-scanner |
| **XposedOrNot** | XposedOrNot | https://xposedornot.com · https://github.com/XposedOrNot |

### Altyapı & Kütüphaneler

| Teknoloji | Bağlantı |
|-----------|----------|
| FastAPI | https://fastapi.tiangolo.com |
| Celery | https://docs.celeryq.org |
| React | https://react.dev |
| PostgreSQL | https://www.postgresql.org |
| Redis | https://redis.io |
| Anthropic Claude *(opsiyonel AI katmanı)* | https://www.anthropic.com |

### Veri Kaynakları

- **Gravatar API** — https://gravatar.com
- **Google Public DNS** — https://developers.google.com/speed/public-dns
- **WhatsMyName JSON veritabanı** — [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) lisansı altında (Micah Hoffman)

### Geliştirme

- **Tunel** — Kağan Haciosmanoğlu ([@kagannhoo](https://github.com/kagannhoo))
- Proje mimarisi ve kod geliştirme sürecinde **[Cursor](https://cursor.com)** AI asistanı (Anthropic Claude) kullanılmıştır.

> Bu araçlar bağımsız projelerdir; Tunel resmi olarak bunların hiçbiri tarafından onaylanmamıştır.

---

## Lisans

[MIT](LICENSE)
