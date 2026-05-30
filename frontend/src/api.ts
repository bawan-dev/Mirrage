import type { HealthStatus, SystemStatus, VoiceStatus } from './types';

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return (await response.json()) as T;
}

export function getSystemStatus(): Promise<SystemStatus> {
  return fetchJson<SystemStatus>('/api/system/status');
}

export function getVoiceStatus(): Promise<VoiceStatus> {
  return fetchJson<VoiceStatus>('/api/voice/status');
}

export function getHealthStatus(): Promise<HealthStatus> {
  return fetchJson<HealthStatus>('/health');
}
