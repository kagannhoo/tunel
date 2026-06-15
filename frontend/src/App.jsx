import { useCallback, useEffect, useState } from "react";
import { getPdfUrl, getScanResult, startScan } from "./api";
import "./App.css";

const STATUS_LABELS = {
  queued: "Kuyrukta bekleniyor...",
  running: "OSINT araçları çalışıyor...",
  done: "Tarama tamamlandı",
  failed: "Tarama başarısız",
};

const SEVERITY_CLASS = {
  kritik: "severity-kritik",
  yüksek: "severity-yuksek",
  orta: "severity-orta",
  düşük: "severity-dusuk",
};

function RiskCard({ analysis }) {
  if (!analysis) return null;
  const level = analysis.risk_level || "düşük";

  return (
    <div className="card card-highlight">
      <h3>🛡️ AI Risk Analizi</h3>
      <div className="risk-card">
        <div className={`risk-score-ring risk-${level}`}>
          {analysis.risk_score ?? "—"}
        </div>
        <div className="risk-body">
          <span className={`badge risk-${level}`}>{level}</span>
          {analysis.executive_summary && (
            <p className="executive-summary">{analysis.executive_summary}</p>
          )}
          <p className="risk-summary">{analysis.summary}</p>
          {analysis.attack_surface && (
            <p className="attack-surface">
              <strong>Saldırı yüzeyi:</strong> {analysis.attack_surface}
            </p>
          )}
        </div>
      </div>

      {analysis.critical_findings?.length > 0 && (
        <div className="subsection">
          <h4>⚠️ Kritik Bulgular</h4>
          <ul className="critical-list">
            {analysis.critical_findings.map((f, i) => (
              <li key={i}>{f}</li>
            ))}
          </ul>
        </div>
      )}

      {analysis.risk_factors?.length > 0 && (
        <div className="subsection">
          <h4>📊 Risk Faktörleri</h4>
          <div className="risk-factors">
            {analysis.risk_factors.map((rf, i) => (
              <div key={i} className={`risk-factor ${SEVERITY_CLASS[rf.severity] || ""}`}>
                <span className="rf-title">{rf.title}</span>
                <span className="rf-detail">{rf.detail}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {analysis.recommendations?.length > 0 && (
        <div className="subsection">
          <h4>✅ Önerilen Aksiyonlar</h4>
          <ul className="recommendations">
            {analysis.recommendations.map((r, i) => (
              <li key={i}>
                <span className={`badge badge-priority-${r.priority || "orta"}`}>
                  {r.priority || "orta"}
                </span>
                {r.action || r}
              </li>
            ))}
          </ul>
        </div>
      )}

      {analysis.errors_and_gaps?.length > 0 && (
        <div className="subsection">
          <h4>🔧 Tarama Hataları / Eksikler</h4>
          <ul className="error-list">
            {analysis.errors_and_gaps.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        </div>
      )}

      {analysis.timeline?.length > 0 && (
        <div className="subsection">
          <h4>📅 Zaman Çizelgesi</h4>
          <div className="timeline">
            {analysis.timeline.map((t, i) => (
              <div key={i} className="timeline-item">
                <span className="timeline-year">{t.year}</span>
                <span>{t.event}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {analysis.coverage && (
        <div className="coverage-bar">
          <span>E-posta: {analysis.coverage.email_scan_found} kayıt</span>
          <span>Sherlock: {analysis.coverage.sherlock_found} platform</span>
          <span>Sızıntı: {analysis.coverage.breach_count}</span>
          <span>Paste: {analysis.coverage.paste_count}</span>
        </div>
      )}
    </div>
  );
}

function PlatformsCard({ platforms, title = "🔍 Platform Taraması" }) {
  if (!platforms) return null;
  const found = platforms.found || [];
  const sources = platforms.sources || {};

  return (
    <div className="card">
      <h3>
        {title}
        <span className="badge badge-count">{found.length} bulundu</span>
      </h3>
      {Object.keys(sources).length > 0 && (
        <div className="source-bar">
          {Object.entries(sources).map(([name, s]) => (
            <span key={name} className="source-chip">
              {name}: <strong>{s.found}</strong>/{s.checked}
            </span>
          ))}
        </div>
      )}
      {platforms.errors?.length > 0 && (
        <p className="warn-text">{platforms.errors.join(" · ")}</p>
      )}
      {platforms.error && <p className="warn-text">{platforms.error}</p>}
      {found.length === 0 ? (
        <p className="muted">Platform bulunamadı.</p>
      ) : (
        <div className="platform-list">
          {found.map((p, i) => (
            <div className="platform-item" key={i}>
              <span>
                {p.platform}
                {p.source && <span className="source-badge">{p.source}</span>}
              </span>
              {p.url && (
                <a href={p.url} target="_blank" rel="noreferrer">{p.url}</a>
              )}
            </div>
          ))}
        </div>
      )}
      {platforms.total_checked > 0 && (
        <p className="meta-text">{platforms.total_checked} site kontrol edildi</p>
      )}
    </div>
  );
}

function BreachesCard({ breaches }) {
  if (!breaches) return null;
  const list = breaches.breaches || [];
  return (
    <div className="card">
      <h3>
        🔓 Veri Sızıntıları
        <span className="badge badge-count">{list.length}</span>
      </h3>
      {breaches.error && <p className="warn-text">{breaches.error}</p>}
      {breaches.has_password_exposure && (
        <p className="critical-text">⛔ Şifre verisi sızıntılarda tespit edildi!</p>
      )}
      {!breaches.breached && !breaches.error && (
        <p className="success-text">✓ Bilinen sızıntı veritabanlarında kayıt yok.</p>
      )}
      {list.map((b, i) => (
        <div className="breach-item" key={i}>
          <strong>{b.name}</strong>
          <div className="breach-date">{b.date} {b.domain && `· ${b.domain}`}</div>
          {b.details && <p className="breach-details">{b.details}</p>}
          <div className="breach-tags">
            {b.data_classes?.map((dc, j) => (
              <span key={j} className="tag">{dc}</span>
            ))}
          </div>
        </div>
      ))}
      {breaches.pastes?.length > 0 && (
        <div className="subsection">
          <h4>📋 Paste Sızıntıları ({breaches.paste_count})</h4>
          {breaches.pastes.map((p, i) => (
            <div key={i} className="paste-item">{p.source} {p.date && `— ${p.date}`}</div>
          ))}
        </div>
      )}
    </div>
  );
}

function RegistrationsCard({ registrations }) {
  if (!registrations) return null;
  const services = registrations.registered_services || [];
  const stats = registrations.stats || {};
  return (
    <div className="card">
      <h3>
        📧 Kayıtlı Servisler (User-Scanner)
        <span className="badge badge-count">{services.length}</span>
      </h3>
      {registrations.error && <p className="warn-text">{registrations.error}</p>}
      {stats.modules_total > 0 && (
        <p className="meta-text">
          {stats.modules_total} modül · {stats.modules_found || 0} bulundu · {stats.modules_errored || 0} hata · {stats.modules_skipped || 0} atlandı
        </p>
      )}
      {services.length === 0 && !registrations.error ? (
        <p className="muted">Kayıt bulunamadı.</p>
      ) : (
        <div className="platform-list">
          {services.map((s, i) => (
            <div className="platform-item" key={i}>
              <span>{s.name}</span>
              <div className="hints">
                {s.emailrecovery && <span className="hint">kurtarma: {s.emailrecovery}</span>}
                {s.phoneNumber && <span className="hint">tel: {s.phoneNumber}</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function EmailIntelCard({ intel }) {
  if (!intel || intel.error) return null;
  const gravatar = intel.gravatar || {};
  return (
    <div className="card">
      <h3>🔬 E-posta İstihbaratı</h3>
      <div className="intel-grid">
        <div><strong>Domain:</strong> {intel.domain}</div>
        <div><strong>Kullanıcı adı türetildi:</strong> {intel.derived_username || "—"}</div>
        <div><strong>Mail sağlayıcı:</strong> {intel.dns?.mail_provider || "—"}</div>
        {intel.is_disposable && <div className="critical-text">⚠ Geçici e-posta domaini</div>}
      </div>
      {gravatar.exists && (
        <div className="subsection">
          <h4>Gravatar Profili</h4>
          <p>{gravatar.display_name} {gravatar.username && `(@${gravatar.username})`}</p>
          {gravatar.accounts?.length > 0 && (
            <div className="platform-list">
              {gravatar.accounts.map((a, i) => (
                <div key={i} className="platform-item">
                  <span>{a.domain}</span>
                  {a.url && <a href={a.url} target="_blank" rel="noreferrer">{a.username}</a>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      {intel.pivot_links && (
        <div className="subsection">
          <h4>OSINT Pivot Linkleri</h4>
          <div className="pivot-links">
            {Object.entries(intel.pivot_links).map(([k, url]) => (
              <a key={k} href={url} target="_blank" rel="noreferrer" className="pivot-link">{k}</a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function App() {
  const [targetType, setTargetType] = useState("username");
  const [target, setTarget] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [taskId, setTaskId] = useState(null);
  const [status, setStatus] = useState(null);
  const [data, setData] = useState(null);

  const pollResult = useCallback(async (id) => {
    try {
      const res = await getScanResult(id);
      setStatus(res.status);
      if (res.status === "done") {
        setData(res.data);
        setLoading(false);
        return true;
      }
      if (res.status === "failed") {
        setError(res.error || "Tarama başarısız oldu");
        setLoading(false);
        return true;
      }
      return false;
    } catch (e) {
      setError(e.message);
      setLoading(false);
      return true;
    }
  }, []);

  useEffect(() => {
    if (!taskId || !loading) return;
    const interval = setInterval(async () => {
      const done = await pollResult(taskId);
      if (done) clearInterval(interval);
    }, 3000);
    return () => clearInterval(interval);
  }, [taskId, loading, pollResult]);

  async function handleScan(e) {
    e.preventDefault();
    setError(null);
    setData(null);
    setStatus(null);
    setLoading(true);
    try {
      const res = await startScan(target.trim(), targetType);
      setTaskId(res.task_id);
      setStatus(res.status);
    } catch (e) {
      setError(e.message);
      setLoading(false);
    }
  }

  const platforms = data?.platforms || data?.username_platforms;

  return (
    <div className="app">
      <header className="header">
        <div className="brand">
          <span className="brand-prompt">~/osint $</span>
          <h1>
            Tun<span className="brand-accent">el</span>
          </h1>
          <span className="brand-cursor" aria-hidden="true">▋</span>
        </div>
        <p className="brand-sub">OSINT intelligence terminal · parallel scan · AI risk engine</p>
        <div className="brand-tags">
          <span className="tag-pill">sherlock</span>
          <span className="tag-pill">wmn</span>
          <span className="tag-pill">user-scanner</span>
          <span className="tag-pill">xon</span>
        </div>
      </header>

      <form className="scan-form" onSubmit={handleScan}>
        <div className="form-row">
          <div className="type-toggle">
            <button type="button" className={targetType === "username" ? "active" : ""} onClick={() => setTargetType("username")}>Kullanıcı Adı</button>
            <button type="button" className={targetType === "email" ? "active" : ""} onClick={() => setTargetType("email")}>E-posta</button>
          </div>
          <input className="scan-input" type="text" placeholder={targetType === "username" ? "örn. johndoe" : "örn. user@gmail.com"} value={target} onChange={(e) => setTarget(e.target.value)} required disabled={loading} />
          <button className="scan-btn" type="submit" disabled={loading || !target.trim()}>
            {loading ? "Taranıyor..." : "Taramayı Başlat"}
          </button>
        </div>
        {error && <div className="error-banner">{error}</div>}
      </form>

      {loading && status && (
        <div className="status-bar">
          <div className="pulse" />
          <span>{STATUS_LABELS[status] || status}</span>
          <span className="mono status-id">{taskId?.slice(0, 8)}...</span>
        </div>
      )}

      {data && (
        <div className="results-grid">
          <RiskCard analysis={data.ai_analysis} />
          <EmailIntelCard intel={data.email_intel} />
          {platforms && (
            <PlatformsCard
              platforms={platforms}
              title="🔍 Platform Taraması"
            />
          )}
          {(data.breaches || data.registrations) && (
            <div className="two-col">
              <BreachesCard breaches={data.breaches} />
              <RegistrationsCard registrations={data.registrations} />
            </div>
          )}
          {taskId && (
            <a className="pdf-btn" href={getPdfUrl(taskId)} target="_blank" rel="noreferrer">📄 PDF Rapor İndir</a>
          )}
        </div>
      )}

      {!loading && !data && !error && (
        <div className="empty-state">
          <span>🔎</span>
          <p>Bir kullanıcı adı veya e-posta girerek OSINT taraması başlatın.</p>
          <p className="muted">Tarama birkaç dakika sürebilir.</p>
        </div>
      )}
    </div>
  );
}
