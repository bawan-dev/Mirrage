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
