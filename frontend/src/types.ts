// Shapes returned by the Mirrage backend API.
// These mirror the Pydantic schemas in backend/app.

export interface HealthStatus {
  service: string;
  status: string;
}

export interface SystemStatus {
  status: string;
  frontend: string;
  backend: string;
  ai: string;
  voice: string;
  hardware: string;
}

export interface VoiceStatus {
  status: string;
  listening: boolean;
  wake_word: string;
  wake_phrase?: string;
  wake_word_engine?: string;
  wake_word_mode?: string;
  local_wake_engine?: string;
  local_wake_engine_provider?: string;
  sensitivity?: number;
  microphone_device?: string | null;
  presence_state?: PresenceState;
  speech_to_text: string;
  text_to_speech: string;
}

export interface WakeEngineStatus {
  enabled: boolean;
  configured: boolean;
  provider: string;
  phrase: string;
  sensitivity: number;
  microphone_device: string | null;
  microphone_configured: boolean;
  model_configured: boolean;
  running: boolean;
  status: string;
  sample_rate: number;
  frame_ms: number;
  cooldown_seconds: number;
  last_detection_time: string | null;
  last_detection_latency_ms: number | null;
  error_message: string | null;
  message: string;
}

export type PresenceState =
  | 'sleeping'
  | 'idle'
  | 'wake_detected'
  | 'listening'
  | 'processing'
  | 'speaking'
  | 'returning_to_idle';

export interface PresenceSnapshot {
  state: PresenceState;
  previous_state: PresenceState | null;
  event: string;
  sequence: number;
  wake_phrase: string;
  wake_word_enabled: boolean;
  wake_word_engine: string;
  transcript: string | null;
  interim_transcript: string | null;
  assistant_reply: string | null;
  source: string;
  message: string;
  updated_at: string;
}

export interface PresenceSettings {
  wake_word_enabled: boolean;
  wake_phrase: string;
  wake_word_engine: string;
  sensitivity: number;
  microphone_device: string | null;
  inactivity_timeout_seconds: number;
  automatic_sleep: boolean;
  privacy_mode: string;
  message: string;
}

export interface PresenceTransition {
  state: PresenceState;
  event?: string;
  transcript?: string;
  interim_transcript?: string;
  assistant_reply?: string;
  source?: string;
  message?: string;
}

export interface AssistantReply {
  reply: string;
  provider: string;
  model: string | null;
  memory_action?: string | null;
  context_action?: string | null;
}

export type AgentType =
  | 'planning'
  | 'memory'
  | 'calendar'
  | 'smart_home'
  | 'research';

export type AgentRunStatus =
  | 'draft'
  | 'planning'
  | 'awaiting_approval'
  | 'awaiting_user_input'
  | 'ready'
  | 'running'
  | 'paused'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'expired';

export interface AgentStatus {
  enabled: boolean;
  database_status: string;
  active_run_count: number;
  awaiting_approval_count: number;
  failed_run_count: number;
  queue_status: string;
  concurrency_limit: number;
  max_steps: number;
  max_runtime_seconds: number;
  message: string;
}

export interface AgentTypeInfo {
  name: AgentType;
  description: string;
  side_effects_allowed: boolean;
  live_web_access: boolean;
}

export interface AgentRun {
  public_id: string;
  owner_user_id: string;
  created_by_device_id: string | null;
  agent_type: AgentType;
  goal: string;
  status: AgentRunStatus;
  risk_level: string;
  current_step: number;
  total_steps: number;
  max_steps: number;
  provider: string | null;
  model: string | null;
  assumptions: string[];
  expected_outcome: string | null;
  stop_conditions: string[];
  clarification_prompt: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  paused_at: string | null;
  cancelled_at: string | null;
  expires_at: string;
  final_result: string | null;
  error_summary: string | null;
  correlation_id: string;
}

export interface AgentStep {
  public_id: string;
  run_id: string;
  step_number: number;
  description: string;
  tool_name: string;
  status: string;
  risk_level: string;
  approval_required: boolean;
  approval_id: string | null;
  approval_status: string | null;
  started_at: string | null;
  completed_at: string | null;
  retry_count: number;
  output_summary: string | null;
  error_summary: string | null;
}

export interface AgentRunDetail {
  run: AgentRun;
  steps: AgentStep[];
}

export interface AgentEvent {
  public_id: string;
  run_id: string;
  step_id: string | null;
  sequence: number;
  event_type: string;
  message: string;
  created_at: string;
}

export interface AgentApproval {
  approval_id: string;
  run_id: string;
  step_id: string;
  requesting_user_id: string;
  agent_type: AgentType;
  tool_name: string;
  description: string;
  risk_level: string;
  expires_at: string;
}

export interface AgentApprovalDecision {
  approval_id: string;
  run_id: string;
  step_id: string;
  status: 'approved' | 'denied';
}

export interface WeatherInfo {
  status: string;
  location: string;
  temperature_c: number | null;
  condition: string;
  updated: string | null;
}

export interface CalendarStatus {
  configured: boolean;
  authenticated: boolean;
  login_url: string | null;
  calendar_id: string;
  scopes: string[];
  message: string;
}

export interface CalendarEvent {
  id: string;
  title: string;
  start: string;
  end: string | null;
  is_all_day: boolean;
  location: string | null;
  calendar: string | null;
  html_link: string | null;
}

export interface CalendarSchedule {
  status: string;
  authenticated: boolean;
  date: string;
  time_zone: string;
  events: CalendarEvent[];
  updated: string | null;
  message: string;
}

export interface SpotifyStatus {
  configured: boolean;
  authenticated: boolean;
  login_url: string | null;
  scopes: string[];
  message: string;
}

export interface SpotifyPlayback {
  status: string;
  authenticated: boolean;
  is_playing: boolean;
  title: string | null;
  artist: string | null;
  album: string | null;
  artwork_url: string | null;
  progress_ms: number | null;
  duration_ms: number | null;
  device_name: string | null;
  device_type: string | null;
  spotify_url: string | null;
  updated: string | null;
  message: string;
}

export interface SpotifyActionResult {
  status: string;
  message: string;
}

export interface MemoryRecord {
  id: number;
  kind: 'preference' | 'fact' | 'goal' | 'routine';
  key: string;
  value: string;
  status: 'active' | 'archived' | 'done';
  source: string | null;
  created_at: string;
  updated_at: string;
}

export interface ContextWeatherSummary {
  status: string;
  location: string;
  temperature_c: number | null;
  condition: string;
  summary: string;
  updated: string | null;
  message: string;
}

export interface ContextCalendarSummary {
  status: string;
  authenticated: boolean;
  today_event_count: number;
  upcoming_event_count: number;
  today_events: CalendarEvent[];
  upcoming_events: CalendarEvent[];
  message: string;
}

export interface ContextMemorySummary {
  status: string;
  preferences: MemoryRecord[];
  goals: MemoryRecord[];
  routines: MemoryRecord[];
  facts_count: number;
  message: string;
}

export interface ContextFocusSuggestion {
  title: string;
  reason: string;
  source: string;
  priority: string;
}

export interface DailyContext {
  status: string;
  date: string;
  generated_at: string;
  weather: ContextWeatherSummary;
  calendar: ContextCalendarSummary;
  memory: ContextMemorySummary;
  suggested_focus: ContextFocusSuggestion[];
  message: string;
}

export interface ProactiveSummary {
  status: string;
  generated_at: string;
  priority: 'none' | 'low' | 'medium' | 'high' | string;
  headline: string;
  message: string;
  suggestions: string[];
  sources: string[];
  should_interrupt: boolean;
}

export interface SmartHomeStatus {
  enabled: boolean;
  configured: boolean;
  provider: string;
  connection_status: string;
  entity_count: number;
  supported_domains: string[];
  last_successful_sync: string | null;
  message: string;
}

export interface SmartHomeEntity {
  entity_id: string;
  name: string;
  domain: string;
  device_type: 'light' | 'switch' | 'scene' | 'sensor' | string;
  state: string;
  available: boolean;
  room: string | null;
  friendly_name: string | null;
  supported_actions: string[];
  last_updated: string | null;
}

export interface SmartHomeEntitiesResponse {
  status: string;
  provider: string;
  items: SmartHomeEntity[];
  count: number;
  message: string;
}

export interface SmartHomeActionResult {
  status: string;
  message: string;
  entity: SmartHomeEntity | null;
}

export interface IdentityPrincipal {
  authenticated: boolean;
  user_id: string | null;
  display_name: string;
  role: string;
  device_id: string | null;
  authentication_method:
    | 'anonymous'
    | 'development'
    | 'trusted_device'
    | 'future_multi_factor';
  assurance_level: 'anonymous' | 'low' | 'trusted_device' | 'strong';
  permissions: string[];
  correlation_id: string;
  device_type: string | null;
  human_session_active: boolean;
  human_session_id: string | null;
}

export type ProfileVisibility =
  | 'private'
  | 'relationship'
  | 'household'
  | 'public';

export interface PersonalizationProfile {
  user_id: string;
  preferred_display_name: string;
  preferred_language: string;
  response_tone: 'neutral' | 'direct' | 'warm' | 'formal';
  response_length: 'concise' | 'balanced' | 'detailed';
  greeting_style: 'none' | 'minimal' | 'standard' | 'warm';
  humour: 'off' | 'light';
  proactivity: 'silent' | 'low' | 'standard' | 'high';
  quiet_hours_start: string | null;
  quiet_hours_end: string | null;
  time_zone: string;
  spoken_announcements: boolean;
  personalized_greeting: boolean;
  cloud_personalization_opt_in: boolean;
  visibility: Record<string, ProfileVisibility>;
  created_at: string;
  updated_at: string;
}

export type PersonalizationProfileUpdate = Partial<
  Omit<PersonalizationProfile, 'user_id' | 'created_at' | 'updated_at'>
>;

export interface VisibleProfile {
  user_id: string;
  fields: Record<string, string | boolean | null>;
  visible_fields: string[];
}

export interface Relationship {
  public_id: string;
  user_a_id: string;
  user_b_id: string;
  proposed_by_user_id: string;
  proposed_to_user_id: string;
  relationship_type: string;
  custom_label: string | null;
  status: 'pending' | 'active' | 'rejected' | 'archived';
  created_at: string;
  updated_at: string;
  responded_at: string | null;
  archived_at: string | null;
}

export interface RelationshipList {
  items: Relationship[];
  count: number;
}

export interface SharedContextItem {
  public_id: string;
  owner_user_id: string;
  context_type: 'plan' | 'reminder' | 'fact' | 'project' | 'preference';
  title: string;
  value: string;
  visibility: ProfileVisibility;
  status: 'active' | 'archived';
  shared_with_user_ids: string[];
  created_at: string;
  updated_at: string;
  archived_at: string | null;
}

export interface SharedContextList {
  items: SharedContextItem[];
  count: number;
}

export interface HumanSession {
  public_id: string;
  user_id: string;
  device_id: string;
  status: 'active' | 'ended' | 'expired';
  created_at: string;
  expires_at: string;
  ended_at: string | null;
  last_seen_at: string | null;
}

export interface HumanSessionEnrollment {
  session: HumanSession;
  token: string;
  message: string;
}

export interface IdentityUser {
  public_id: string;
  display_name: string;
  role: 'owner' | 'family' | 'trusted_guest' | 'guest' | 'service';
  status: 'active' | 'disabled';
  household_member: boolean;
  created_at: string;
  updated_at: string;
  disabled_at: string | null;
}

export interface TrustedDevice {
  public_id: string;
  user_id: string;
  display_name: string;
  device_type: string;
  trust_level: string;
  status: 'active' | 'revoked' | 'pending';
  created_at: string;
  last_seen_at: string | null;
  revoked_at: string | null;
  metadata: Record<string, unknown>;
}

export interface Approval {
  public_id: string;
  requester_user_id: string;
  requester_device_id: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  risk_level: string;
  status: string;
  reason: string;
  requested_at: string;
  expires_at: string;
  decided_at: string | null;
  decided_by_user_id: string | null;
  decision_reason: string | null;
  correlation_id: string;
}

export interface ApprovalList {
  items: Approval[];
  count: number;
}

export interface AuditEvent {
  public_id: string;
  timestamp: string;
  event_type: string;
  actor_user_id: string | null;
  actor_role: string | null;
  device_id: string | null;
  authentication_method: string | null;
  action: string | null;
  resource_type: string | null;
  resource_id: string | null;
  authorization_decision: string | null;
  risk_level: string | null;
  reason: string | null;
  result: string | null;
  correlation_id: string | null;
  metadata: Record<string, unknown>;
}

export interface AuditEventList {
  items: AuditEvent[];
  count: number;
  limit: number;
  offset: number;
}
