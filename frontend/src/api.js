const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function startScan(target, targetType) {
  const res = await fetch(`${API_URL}/scan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ target, target_type: targetType }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function getScanResult(taskId) {
  const res = await fetch(`${API_URL}/scan/${taskId}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export function getPdfUrl(taskId) {
  return `${API_URL}/scan/${taskId}/pdf`;
}

export async function getLogs() {
  const res = await fetch(`${API_URL}/logs`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
