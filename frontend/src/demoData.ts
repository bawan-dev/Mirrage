import type {
  CalendarSchedule,
  CalendarStatus,
  DailyContext,
  HealthStatus,
  IdentityPrincipal,
  IdentityUser,
  PresenceSettings,
  PresenceSnapshot,
  ProactiveSummary,
  SmartHomeEntitiesResponse,
  SmartHomeStatus,
  SpotifyPlayback,
  SpotifyStatus,
  SystemStatus,
  TrustedDevice,
  VoiceStatus,
  WakeEngineStatus,
  WeatherInfo,
} from './types';

export const demoIdentityPrincipal: IdentityPrincipal = {
  authenticated: true,
  user_id: 'demo-owner',
  display_name: 'Sample Owner',
  role: 'owner',
  device_id: 'demo-mirror',
  authentication_method: 'development',
  assurance_level: 'low',
  permissions: ['identity.users.read', 'identity.devices.read', 'audit.read'],
  correlation_id: 'demo-correlation',
};

export const demoIdentityUsers: IdentityUser[] = [
  {
    public_id: 'demo-owner',
    display_name: 'Sample Owner',
    role: 'owner',
    status: 'active',
    household_member: true,
    created_at: '2026-07-18T08:00:00Z',
    updated_at: '2026-07-18T08:00:00Z',
    disabled_at: null,
  },
  {
    public_id: 'demo-family',
    display_name: 'Sample Family',
    role: 'family',
    status: 'active',
    household_member: true,
    created_at: '2026-07-18T08:10:00Z',
    updated_at: '2026-07-18T08:10:00Z',
    disabled_at: null,
  },
  {
    public_id: 'demo-guest',
    display_name: 'Sample Guest',
    role: 'guest',
    status: 'active',
    household_member: false,
    created_at: '2026-07-18T08:20:00Z',
    updated_at: '2026-07-18T08:20:00Z',
    disabled_at: null,
  },
];

export const demoTrustedDevices: TrustedDevice[] = [
  {
    public_id: 'demo-mirror',
    user_id: 'demo-owner',
    display_name: 'Sample Mirror',
    device_type: 'mirror',
    trust_level: 'privileged',
    status: 'active',
    created_at: '2026-07-18T08:00:00Z',
    last_seen_at: '2026-07-18T12:00:00Z',
    revoked_at: null,
    metadata: {},
  },
];

const now = new Date();
const today = now.toISOString().slice(0, 10);

const todayAt = (hour: number, minute = 0) => {
  const value = new Date(now);
  value.setHours(hour, minute, 0, 0);
  return value.toISOString();
};

export const demoHealthStatus: HealthStatus = {
  service: 'mirrage-api',
  status: 'online',
};

export const demoSystemStatus: SystemStatus = {
  ai: 'runtime ready',
  backend: 'online',
  frontend: 'running',
  hardware: 'planned',
  status: 'online',
  voice: 'browser voice ready',
};

export const demoVoiceStatus: VoiceStatus = {
  listening: false,
  local_wake_engine: 'prepared',
  local_wake_engine_provider: 'openwakeword',
  presence_state: 'idle',
  speech_to_text: 'browser',
  status: 'ready',
  text_to_speech: 'browser',
  wake_phrase: 'Hey Mirrage',
  wake_word: 'configured',
  wake_word_engine: 'openwakeword',
  wake_word_mode: 'local boundary',
};

export const demoWeather: WeatherInfo = {
  condition: 'Overcast, calm wind',
  location: 'London',
  status: 'online',
  temperature_c: 15,
  updated: now.toISOString(),
};

export const demoPresenceSnapshot: PresenceSnapshot = {
  assistant_reply: null,
  event: 'demo_presence_ready',
  interim_transcript: null,
  message: 'Demo presence is ready.',
  previous_state: null,
  sequence: 1,
  source: 'demo',
  state: 'idle',
  transcript: null,
  updated_at: now.toISOString(),
  wake_phrase: 'Hey Mirrage',
  wake_word_enabled: true,
  wake_word_engine: 'openwakeword',
};

export const demoPresenceSettings: PresenceSettings = {
  automatic_sleep: true,
  inactivity_timeout_seconds: 25,
  message: 'Demo wake settings are loaded.',
  microphone_device: 'Default microphone',
  privacy_mode: 'local-first',
  sensitivity: 0.5,
  wake_phrase: 'Hey Mirrage',
  wake_word_enabled: true,
  wake_word_engine: 'openwakeword',
};

export const demoWakeEngineStatus: WakeEngineStatus = {
  configured: false,
  cooldown_seconds: 3,
  enabled: false,
  error_message: null,
  frame_ms: 80,
  last_detection_latency_ms: null,
  last_detection_time: null,
  message: 'Wake engine boundary is prepared; real model testing is pending.',
  microphone_configured: false,
  microphone_device: null,
  model_configured: false,
  phrase: 'Hey Mirrage',
  provider: 'openwakeword',
  running: false,
  sample_rate: 16000,
  sensitivity: 0.5,
  status: 'demo-ready',
};

export const demoCalendarStatus: CalendarStatus = {
  authenticated: true,
  calendar_id: 'primary',
  configured: true,
  login_url: null,
  message: 'Demo calendar data is loaded.',
  scopes: ['readonly events'],
};

export const demoCalendarToday: CalendarSchedule = {
  authenticated: true,
  date: today,
  events: [
    {
      calendar: 'primary',
      end: todayAt(10, 30),
      html_link: null,
      id: 'demo-standup',
      is_all_day: false,
      location: 'Studio desk',
      start: todayAt(10, 0),
      title: 'Mirrage v1 release review',
    },
    {
      calendar: 'primary',
      end: todayAt(15, 0),
      html_link: null,
      id: 'demo-hardware',
      is_all_day: false,
      location: 'Workshop',
      start: todayAt(14, 0),
      title: 'Mirror material brightness test',
    },
  ],
  message: 'Two demo events today.',
  status: 'ready',
  time_zone: 'Europe/London',
  updated: now.toISOString(),
};

export const demoCalendarUpcoming: CalendarSchedule = {
  authenticated: true,
  date: today,
  events: [
    {
      calendar: 'primary',
      end: todayAt(11, 0),
      html_link: null,
      id: 'demo-interview',
      is_all_day: false,
      location: 'Remote',
      start: todayAt(10, 30),
      title: 'Portfolio walkthrough',
    },
  ],
  message: 'One upcoming demo event.',
  status: 'ready',
  time_zone: 'Europe/London',
  updated: now.toISOString(),
};

export const demoDailyContext: DailyContext = {
  calendar: {
    authenticated: true,
    message: 'Two events today, with one hardware validation block.',
    status: 'ready',
    today_event_count: 2,
    today_events: demoCalendarToday.events,
    upcoming_event_count: 1,
    upcoming_events: demoCalendarUpcoming.events,
  },
  date: today,
  generated_at: now.toISOString(),
  memory: {
    facts_count: 1,
    goals: [
      {
        created_at: now.toISOString(),
        id: 1,
        key: 'goal: finish Mirrage v1 polish',
        kind: 'goal',
        source: 'demo',
        status: 'active',
        updated_at: now.toISOString(),
        value: 'Prepare the first polished Mirrage release.',
      },
    ],
    message: 'Demo memory has one active goal.',
    preferences: [
      {
        created_at: now.toISOString(),
        id: 2,
        key: 'preference: quiet interface',
        kind: 'preference',
        source: 'demo',
        status: 'active',
        updated_at: now.toISOString(),
        value: 'Keep the mirror calm and voice-first.',
      },
    ],
    routines: [],
    status: 'ready',
  },
  message: 'Demo daily context is ready.',
  status: 'ready',
  suggested_focus: [
    {
      priority: 'high',
      reason: 'Release polish is the highest leverage task before recording.',
      source: 'memory',
      title: 'Finish Mirrage v1 polish',
    },
  ],
  weather: {
    condition: demoWeather.condition,
    location: demoWeather.location,
    message: 'Demo weather is loaded.',
    status: 'ready',
    summary: '15C and overcast in London.',
    temperature_c: demoWeather.temperature_c,
    updated: demoWeather.updated,
  },
};

export const demoProactiveSummary: ProactiveSummary = {
  generated_at: now.toISOString(),
  headline: 'Release polish first',
  message:
    'Today is clear enough to finish the v1 mirror experience and capture screenshots.',
  priority: 'medium',
  should_interrupt: false,
  sources: ['calendar', 'memory', 'weather'],
  status: 'ready',
  suggestions: ['Finish the assistant presence states', 'Refresh screenshots'],
};

export const demoSpotifyStatus: SpotifyStatus = {
  authenticated: true,
  configured: true,
  login_url: null,
  message: 'Demo Spotify playback is loaded.',
  scopes: ['user-read-playback-state', 'user-modify-playback-state'],
};

export const demoSpotifyPlayback: SpotifyPlayback = {
  album: 'Ambient Systems',
  artist: 'Mirrage Demo',
  artwork_url: null,
  authenticated: true,
  device_name: 'Mirror Room',
  device_type: 'Computer',
  duration_ms: 218000,
  is_playing: true,
  message: 'Demo playback is active.',
  progress_ms: 74000,
  spotify_url: null,
  status: 'playing',
  title: 'Glass Surface',
  updated: now.toISOString(),
};

export const demoSmartHomeStatus: SmartHomeStatus = {
  configured: true,
  connection_status: 'connected',
  enabled: true,
  entity_count: 4,
  last_successful_sync: now.toISOString(),
  message: 'Demo Home Assistant entities are loaded.',
  provider: 'home-assistant',
  supported_domains: ['light', 'switch', 'scene', 'sensor'],
};

export const demoSmartHomeEntities: SmartHomeEntitiesResponse = {
  count: 3,
  items: [
    {
      available: true,
      device_type: 'light',
      domain: 'light',
      entity_id: 'light.demo_mirror',
      friendly_name: 'Mirror Accent',
      last_updated: now.toISOString(),
      name: 'Mirror Accent',
      room: 'Bedroom',
      state: 'on',
      supported_actions: ['turn-on', 'turn-off'],
    },
    {
      available: true,
      device_type: 'switch',
      domain: 'switch',
      entity_id: 'switch.demo_frame_fan',
      friendly_name: 'Frame Fan',
      last_updated: now.toISOString(),
      name: 'Frame Fan',
      room: 'Mirror',
      state: 'off',
      supported_actions: ['turn-on', 'turn-off'],
    },
    {
      available: true,
      device_type: 'scene',
      domain: 'scene',
      entity_id: 'scene.demo_evening',
      friendly_name: 'Evening Mirror',
      last_updated: now.toISOString(),
      name: 'Evening Mirror',
      room: 'Bedroom',
      state: 'ready',
      supported_actions: ['activate'],
    },
  ],
  message: 'Demo smart home entities are loaded.',
  provider: 'home-assistant',
  status: 'ready',
};

export const demoSmartHomeSensors: SmartHomeEntitiesResponse = {
  count: 1,
  items: [
    {
      available: true,
      device_type: 'sensor',
      domain: 'sensor',
      entity_id: 'sensor.demo_frame_temperature',
      friendly_name: 'Frame Temperature',
      last_updated: now.toISOString(),
      name: 'Frame Temperature',
      room: 'Mirror',
      state: '31 C',
      supported_actions: [],
    },
  ],
  message: 'Demo sensors are loaded.',
  provider: 'home-assistant',
  status: 'ready',
};
