const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';

async function fetchJson(path) {
  const response = await fetch(`${API_BASE_URL}${path}`);

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return response.json();
}

export function getSystemStatus() {
  return fetchJson('/api/system/status');
}

export function getVoiceStatus() {
  return fetchJson('/api/voice/status');
}

export function getHealthStatus() {
  return fetchJson('/health');
}
