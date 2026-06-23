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
  speech_to_text: string;
  text_to_speech: string;
}

export interface AssistantReply {
  reply: string;
  provider: string;
  model: string | null;
  memory_action?: string | null;
  context_action?: string | null;
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
