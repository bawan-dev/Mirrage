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
