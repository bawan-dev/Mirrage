import type {
  AssistantReply,
  ApprovalList,
  AuditEventList,
  CalendarSchedule,
  CalendarStatus,
  DailyContext,
  HealthStatus,
  IdentityPrincipal,
  IdentityUser,
  HumanSession,
  HumanSessionEnrollment,
  PersonalizationProfile,
  PersonalizationProfileUpdate,
  PresenceSettings,
  PresenceSnapshot,
  PresenceTransition,
  ProactiveSummary,
  Relationship,
  RelationshipList,
  SmartHomeActionResult,
  SmartHomeEntitiesResponse,
  SmartHomeEntity,
  SmartHomeStatus,
  SpotifyActionResult,
  SpotifyPlayback,
  SpotifyStatus,
  SharedContextItem,
  SharedContextList,
  SystemStatus,
  TrustedDevice,
  VoiceStatus,
  WakeEngineStatus,
  WeatherInfo,
} from './types';

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';

let trustedDeviceToken: string | null = null;
let humanSessionToken: string | null = null;

export function setTrustedDeviceToken(token: string | null): void {
  trustedDeviceToken = token?.trim() || null;
}

export function setHumanSessionToken(token: string | null): void {
  humanSessionToken = token?.trim() || null;
}

function requestHeaders(includeJson = false): HeadersInit {
  const headers: Record<string, string> = {};
  if (includeJson) {
    headers['Content-Type'] = 'application/json';
  }
  if (trustedDeviceToken) {
    headers.Authorization = `Bearer ${trustedDeviceToken}`;
  }
  if (humanSessionToken) {
    headers['X-Mirrage-Human-Session'] = humanSessionToken;
  }
  return headers;
}

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: requestHeaders(),
  });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return (await response.json()) as T;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: requestHeaders(true),
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return (await response.json()) as T;
}

async function patchJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'PATCH',
    headers: requestHeaders(true),
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

export function getWakeEngineStatus(): Promise<WakeEngineStatus> {
  return fetchJson<WakeEngineStatus>('/api/wake-word/status');
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

export function getSmartHomeStatus(): Promise<SmartHomeStatus> {
  return fetchJson<SmartHomeStatus>('/api/smart-home/status');
}

export function getSmartHomeEntities(): Promise<SmartHomeEntitiesResponse> {
  return fetchJson<SmartHomeEntitiesResponse>('/api/smart-home/entities');
}

export function getSmartHomeSensors(): Promise<SmartHomeEntitiesResponse> {
  return fetchJson<SmartHomeEntitiesResponse>('/api/smart-home/sensors');
}

export function getSmartHomeEntity(entityId: string): Promise<SmartHomeEntity> {
  return fetchJson<SmartHomeEntity>(
    `/api/smart-home/entities/${encodeURIComponent(entityId)}`,
  );
}

export function runSmartHomeEntityAction(
  entityId: string,
  action: 'turn-on' | 'turn-off',
): Promise<SmartHomeActionResult> {
  return postJson<SmartHomeActionResult>(
    `/api/smart-home/entities/${encodeURIComponent(entityId)}/${action}`,
    {},
  );
}

export function activateSmartHomeScene(
  entityId: string,
): Promise<SmartHomeActionResult> {
  return postJson<SmartHomeActionResult>(
    `/api/smart-home/scenes/${encodeURIComponent(entityId)}/activate`,
    {},
  );
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

export function getIdentityMe(): Promise<IdentityPrincipal> {
  return fetchJson<IdentityPrincipal>('/api/identity/me');
}

export function getIdentityUsers(): Promise<IdentityUser[]> {
  return fetchJson<IdentityUser[]>('/api/identity/users');
}

export function getIdentityDevices(): Promise<TrustedDevice[]> {
  return fetchJson<TrustedDevice[]>('/api/identity/devices');
}

export function getApprovals(): Promise<ApprovalList> {
  return fetchJson<ApprovalList>('/api/approvals?status=pending');
}

export function getAuditEvents(): Promise<AuditEventList> {
  return fetchJson<AuditEventList>('/api/audit/events?limit=8');
}

export function disableIdentityUser(userId: string): Promise<IdentityUser> {
  return postJson<IdentityUser>(
    `/api/identity/users/${encodeURIComponent(userId)}/disable`,
    {},
  );
}

export function revokeTrustedDevice(deviceId: string): Promise<TrustedDevice> {
  return postJson<TrustedDevice>(
    `/api/identity/devices/${encodeURIComponent(deviceId)}/revoke`,
    {},
  );
}

export function createHumanSession(): Promise<HumanSessionEnrollment> {
  return postJson<HumanSessionEnrollment>('/api/sessions', {});
}

export function endHumanSession(): Promise<HumanSession> {
  return postJson<HumanSession>('/api/sessions/current/end', {});
}

export function getMyProfile(): Promise<PersonalizationProfile> {
  return fetchJson<PersonalizationProfile>('/api/profile/me');
}

export function updateMyProfile(
  update: PersonalizationProfileUpdate,
): Promise<PersonalizationProfile> {
  return patchJson<PersonalizationProfile>('/api/profile/me', update);
}

export function getProfileDirectory(): Promise<
  import('./types').VisibleProfile[]
> {
  return fetchJson<import('./types').VisibleProfile[]>(
    '/api/profiles/directory',
  );
}

export function getRelationships(): Promise<RelationshipList> {
  return fetchJson<RelationshipList>('/api/relationships');
}

export function createRelationship(
  targetUserId: string,
  relationshipType: string,
): Promise<Relationship> {
  return postJson<Relationship>('/api/relationships', {
    target_user_id: targetUserId,
    relationship_type: relationshipType,
  });
}

export function answerRelationship(
  relationshipId: string,
  action: 'accept' | 'reject' | 'archive',
): Promise<Relationship> {
  return postJson<Relationship>(
    `/api/relationships/${encodeURIComponent(relationshipId)}/${action}`,
    {},
  );
}

export function getSharedContext(): Promise<SharedContextList> {
  return fetchJson<SharedContextList>('/api/shared-context');
}

export function createSharedContext(input: {
  context_type: SharedContextItem['context_type'];
  title: string;
  value: string;
  visibility: SharedContextItem['visibility'];
}): Promise<SharedContextItem> {
  return postJson<SharedContextItem>('/api/shared-context', input);
}

export function shareContext(
  contextId: string,
  userId: string,
): Promise<SharedContextItem> {
  return postJson<SharedContextItem>(
    `/api/shared-context/${encodeURIComponent(contextId)}/share`,
    { user_id: userId },
  );
}

export function revokeContextShare(
  contextId: string,
  userId: string,
): Promise<SharedContextItem> {
  return postJson<SharedContextItem>(
    `/api/shared-context/${encodeURIComponent(contextId)}/revoke`,
    { user_id: userId },
  );
}

export function archiveSharedContext(
  contextId: string,
): Promise<SharedContextItem> {
  return postJson<SharedContextItem>(
    `/api/shared-context/${encodeURIComponent(contextId)}/archive`,
    {},
  );
}
