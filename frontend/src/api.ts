import type {
  AssistantReply,
  CalendarSchedule,
  CalendarStatus,
  DailyContext,
  HealthStatus,
  PresenceSettings,
  PresenceSnapshot,
  PresenceTransition,
  ProactiveSummary,
  SpotifyActionResult,
  SpotifyPlayback,
  SpotifyStatus,
  SystemStatus,
  VoiceStatus,
  WeatherInfo,
} from './types';

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return (await response.json()) as T;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

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

export function getPresenceStatus(): Promise<PresenceSnapshot> {
  return fetchJson<PresenceSnapshot>('/api/presence/status');
}

export function getPresenceSettings(): Promise<PresenceSettings> {
  return fetchJson<PresenceSettings>('/api/presence/settings');
}

export function getPresenceEventsUrl(): string {
  return `${API_BASE_URL}/api/presence/events`;
}

export function sendPresenceTransition(
  transition: PresenceTransition,
): Promise<PresenceSnapshot> {
  return postJson<PresenceSnapshot>('/api/presence/transition', transition);
}

export function sendWakeWordDetection(
  phrase: string,
  source = 'frontend_wake_listener',
): Promise<PresenceSnapshot> {
  return postJson<PresenceSnapshot>('/api/wake-word/detect', {
    phrase,
    source,
  });
}

export function getHealthStatus(): Promise<HealthStatus> {
  return fetchJson<HealthStatus>('/health');
}

export function getWeather(): Promise<WeatherInfo> {
  return fetchJson<WeatherInfo>('/api/info/weather');
}

export function getDailyContext(): Promise<DailyContext> {
  return fetchJson<DailyContext>('/api/context/daily');
}

export function getProactiveSummary(): Promise<ProactiveSummary> {
  return fetchJson<ProactiveSummary>('/api/proactive/summary');
}

export function sendAssistantMessage(message: string): Promise<AssistantReply> {
  return postJson<AssistantReply>('/api/assistant/message', { message });
}

export function getCalendarStatus(): Promise<CalendarStatus> {
  return fetchJson<CalendarStatus>('/api/integrations/calendar/status');
}

export function getCalendarToday(): Promise<CalendarSchedule> {
  return fetchJson<CalendarSchedule>('/api/integrations/calendar/events/today');
}

export function getCalendarUpcoming(days = 7): Promise<CalendarSchedule> {
  return fetchJson<CalendarSchedule>(
    `/api/integrations/calendar/events/upcoming?days=${days}`,
  );
}

export function getCalendarLoginUrl(): string {
  return `${API_BASE_URL}/api/integrations/calendar/login`;
}

export function getSpotifyStatus(): Promise<SpotifyStatus> {
  return fetchJson<SpotifyStatus>('/api/integrations/spotify/status');
}

export function getSpotifyPlayback(): Promise<SpotifyPlayback> {
  return fetchJson<SpotifyPlayback>(
    '/api/integrations/spotify/player/currently-playing',
  );
}

export function getSpotifyLoginUrl(): string {
  return `${API_BASE_URL}/api/integrations/spotify/login`;
}

export function runSpotifyAction(
  action: 'play' | 'pause' | 'next' | 'previous',
): Promise<SpotifyActionResult> {
  return postJson<SpotifyActionResult>(
    `/api/integrations/spotify/player/${action}`,
    {},
  );
}
