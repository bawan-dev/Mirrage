import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
} from 'react';

import {
  getCalendarLoginUrl,
  getCalendarStatus,
  getCalendarToday,
  getCalendarUpcoming,
  getDailyContext,
  getHealthStatus,
  getProactiveSummary,
  getSpotifyLoginUrl,
  getSpotifyPlayback,
  getSpotifyStatus,
  getSystemStatus,
  getVoiceStatus,
  getWeather,
  runSpotifyAction,
  sendAssistantMessage,
} from './api';
import {
  routeAssistantCommand,
  type AssistantCommandRoute,
  type AssistantUiAction,
} from './intentRouting';
import { mirrorModeConfig } from './config';
import type {
  AssistantReply,
  CalendarEvent,
  CalendarSchedule,
  CalendarStatus,
  DailyContext,
  HealthStatus,
  ProactiveSummary,
  SpotifyPlayback,
  SpotifyStatus,
  SystemStatus,
  VoiceStatus,
  WeatherInfo,
} from './types';

type FocusView =
  | 'home'
  | 'weather'
  | 'assistant'
  | 'media'
  | 'calendar'
  | 'context';

const focusViewValues: FocusView[] = [
  'home',
  'weather',
  'assistant',
  'media',
  'calendar',
  'context',
];

interface BackendState {
  error: string | null;
  isLoading: boolean;
}

interface SpotifyUiState {
  actionMessage: string | null;
  error: string | null;
  isLoading: boolean;
}

interface CalendarUiState {
  error: string | null;
  isLoading: boolean;
}

interface ContextUiState {
  error: string | null;
  isLoading: boolean;
}

interface ProactiveUiState {
  error: string | null;
  isLoading: boolean;
}

type AssistantOrbState =
  | 'error'
  | 'idle'
  | 'listening'
  | 'speaking'
  | 'thinking';

type MirrorInactivityLevel = 'active' | 'dimmed' | 'sleep';

interface BurnInOffset {
  x: number;
  y: number;
}

interface MirrorStartupCheck {
  label: string;
  status: string;
  tone: 'checking' | 'offline' | 'online' | 'planned';
}

interface AssistantMessage {
  role: 'user' | 'assistant';
  text: string;
  meta?: string;
}

interface BrowserSpeechRecognitionAlternative {
  transcript: string;
}

interface BrowserSpeechRecognitionResult {
  isFinal: boolean;
  [index: number]: BrowserSpeechRecognitionAlternative | undefined;
}

interface BrowserSpeechRecognitionEvent extends Event {
  resultIndex: number;
  results: {
    length: number;
    [index: number]: BrowserSpeechRecognitionResult | undefined;
  };
}

interface BrowserSpeechRecognitionErrorEvent extends Event {
  error: string;
}

interface BrowserSpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onend: (() => void) | null;
  onerror: ((event: BrowserSpeechRecognitionErrorEvent) => void) | null;
  onresult: ((event: BrowserSpeechRecognitionEvent) => void) | null;
  abort: () => void;
  start: () => void;
  stop: () => void;
}

interface BrowserSpeechRecognitionConstructor {
  new (): BrowserSpeechRecognition;
}

const focusButtonBase =
  'group rounded-lg border border-line bg-panel p-5 text-left shadow-mirror transition duration-300 hover:-translate-y-1 hover:border-cyan/70 hover:bg-panel-strong focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan';
const labelClass =
  'text-[0.72rem] font-bold uppercase tracking-[0.18em] text-cyan';
const mutedClass = 'text-sm leading-relaxed text-muted';
const focusPanelClass =
  'focus-panel animate-focus-in rounded-xl border border-line bg-panel p-5 shadow-mirror md:p-8';

const burnInOffsets: BurnInOffset[] = [
  { x: 0, y: 0 },
  { x: 4, y: -3 },
  { x: -4, y: 3 },
  { x: 3, y: 4 },
  { x: -3, y: -4 },
  { x: 2, y: -2 },
];

function getInitialFocusView(): FocusView {
  const requestedView = new URLSearchParams(window.location.search).get('view');

  if (focusViewValues.includes(requestedView as FocusView)) {
    return requestedView as FocusView;
  }

  return 'home';
}

function formatStatus(value?: string): string {
  if (!value) {
    return 'Unknown';
  }

  return value
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatTemperature(weather: WeatherInfo | null): string {
  if (
    !weather ||
    weather.temperature_c == null ||
    weather.status !== 'online'
  ) {
    return '-- C';
  }

  return `${Math.round(weather.temperature_c)} C`;
}

function formatUpdated(value: string | null | undefined): string {
  if (!value) {
    return 'Not updated yet';
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
  }).format(parsed);
}

function formatDuration(milliseconds: number | null | undefined): string {
  if (milliseconds == null) {
    return '--:--';
  }

  const totalSeconds = Math.max(0, Math.floor(milliseconds / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;

  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

function formatCalendarEventTime(event: CalendarEvent): string {
  if (event.is_all_day) {
    return 'All day';
  }

  const parsed = new Date(event.start);
  if (Number.isNaN(parsed.getTime())) {
    return event.start;
  }

  return new Intl.DateTimeFormat('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
  }).format(parsed);
}

function formatCalendarEventDateTime(event: CalendarEvent): string {
  if (event.is_all_day) {
    const parsed = new Date(`${event.start}T00:00:00`);
    if (Number.isNaN(parsed.getTime())) {
      return event.start;
    }

    return new Intl.DateTimeFormat('en-GB', {
      day: 'numeric',
      month: 'short',
    }).format(parsed);
  }

  const parsed = new Date(event.start);
  if (Number.isNaN(parsed.getTime())) {
    return event.start;
  }

  return new Intl.DateTimeFormat('en-GB', {
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    month: 'short',
  }).format(parsed);
}

function summarizeCalendarToday(
  schedule: CalendarSchedule,
  status: CalendarStatus | null,
): string {
  if (!status?.configured || schedule.status === 'not_configured') {
    return 'Google Calendar is not configured yet. Add the Calendar OAuth credentials, then connect it from the calendar view.';
  }

  if (!schedule.authenticated || schedule.status === 'not_authenticated') {
    return 'Google Calendar is configured, but it is not connected yet. Open the calendar view and connect your account.';
  }

  if (schedule.events.length === 0) {
    return 'You do not have anything on your calendar today.';
  }

  const visibleEvents = schedule.events
    .slice(0, 3)
    .map((event) => `${formatCalendarEventTime(event)} ${event.title}`)
    .join('; ');
  const remaining = schedule.events.length - 3;

  return `You have ${schedule.events.length} event${
    schedule.events.length === 1 ? '' : 's'
  } today: ${visibleEvents}${remaining > 0 ? `; plus ${remaining} more.` : '.'}`;
}

function getSpeechRecognitionConstructor(): BrowserSpeechRecognitionConstructor | null {
  const speechWindow = window as Window & {
    SpeechRecognition?: BrowserSpeechRecognitionConstructor;
    webkitSpeechRecognition?: BrowserSpeechRecognitionConstructor;
  };

  return (
    speechWindow.SpeechRecognition ??
    speechWindow.webkitSpeechRecognition ??
    null
  );
}

function getVoiceErrorMessage(error: string): string {
  if (error === 'not-allowed' || error === 'service-not-allowed') {
    return 'Microphone permission was blocked.';
  }

  if (error === 'no-speech') {
    return 'No speech was detected.';
  }

  if (error === 'audio-capture') {
    return 'No microphone was found.';
  }

  return `Speech recognition failed: ${error}.`;
}

export default function App() {
  const [activeView, setActiveView] = useState<FocusView>(() =>
    getInitialFocusView(),
  );
  const recognitionRef = useRef<BrowserSpeechRecognition | null>(null);
  const inactivityDimTimerRef = useRef<number | null>(null);
  const inactivitySleepTimerRef = useRef<number | null>(null);
  const [now, setNow] = useState<Date>(() => new Date());
  const isMirrorMode = mirrorModeConfig.enabled;
  const [mirrorInactivityLevel, setMirrorInactivityLevel] =
    useState<MirrorInactivityLevel>('active');
  const [mirrorStartupVisible, setMirrorStartupVisible] =
    useState(isMirrorMode);
  const [burnInIndex, setBurnInIndex] = useState(0);
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [voiceStatus, setVoiceStatus] = useState<VoiceStatus | null>(null);
  const [weather, setWeather] = useState<WeatherInfo | null>(null);
  const [calendarStatus, setCalendarStatus] = useState<CalendarStatus | null>(
    null,
  );
  const [calendarToday, setCalendarToday] = useState<CalendarSchedule | null>(
    null,
  );
  const [calendarUpcoming, setCalendarUpcoming] =
    useState<CalendarSchedule | null>(null);
  const [dailyContext, setDailyContext] = useState<DailyContext | null>(null);
  const [proactiveSummary, setProactiveSummary] =
    useState<ProactiveSummary | null>(null);
  const [spotifyStatus, setSpotifyStatus] = useState<SpotifyStatus | null>(
    null,
  );
  const [spotifyPlayback, setSpotifyPlayback] =
    useState<SpotifyPlayback | null>(null);
  const [backendState, setBackendState] = useState<BackendState>({
    error: null,
    isLoading: true,
  });
  const [spotifyState, setSpotifyState] = useState<SpotifyUiState>({
    actionMessage: null,
    error: null,
    isLoading: true,
  });
  const [calendarState, setCalendarState] = useState<CalendarUiState>({
    error: null,
    isLoading: true,
  });
  const [contextState, setContextState] = useState<ContextUiState>({
    error: null,
    isLoading: true,
  });
  const [proactiveState, setProactiveState] = useState<ProactiveUiState>({
    error: null,
    isLoading: true,
  });
  const [draft, setDraft] = useState('');
  const [assistantBusy, setAssistantBusy] = useState(false);
  const [assistantError, setAssistantError] = useState<string | null>(null);
  const [assistantProvider, setAssistantProvider] = useState<string | null>(
    null,
  );
  const [voiceSupported, setVoiceSupported] = useState(false);
  const [voiceListening, setVoiceListening] = useState(false);
  const [voiceTranscript, setVoiceTranscript] = useState('');
  const [voiceInterimTranscript, setVoiceInterimTranscript] = useState('');
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const [microphoneReady, setMicrophoneReady] = useState(false);
  const speechRequestRef = useRef(0);
  const [ttsSupported, setTtsSupported] = useState(false);
  const [ttsMuted, setTtsMuted] = useState(false);
  const [ttsSpeaking, setTtsSpeaking] = useState(false);
  const [ttsVoices, setTtsVoices] = useState<SpeechSynthesisVoice[]>([]);
  const [ttsVoiceURI, setTtsVoiceURI] = useState('');
  const ttsMutedRef = useRef(false);
  const ttsSupportedRef = useRef(false);
  const ttsVoicesRef = useRef<SpeechSynthesisVoice[]>([]);
  const ttsVoiceURIRef = useRef('');
  const [assistantMessages, setAssistantMessages] = useState<
    AssistantMessage[]
  >([
    {
      role: 'assistant',
      text: 'Assistant route is ready. Real responses depend on the configured provider.',
      meta: 'Provider status appears after the first message.',
    },
  ]);

  const clearMirrorInactivityTimers = useCallback(() => {
    if (inactivityDimTimerRef.current !== null) {
      window.clearTimeout(inactivityDimTimerRef.current);
      inactivityDimTimerRef.current = null;
    }

    if (inactivitySleepTimerRef.current !== null) {
      window.clearTimeout(inactivitySleepTimerRef.current);
      inactivitySleepTimerRef.current = null;
    }
  }, []);

  const registerMirrorActivity = useCallback(() => {
    if (!isMirrorMode) {
      return;
    }

    clearMirrorInactivityTimers();
    setMirrorInactivityLevel('active');

    inactivityDimTimerRef.current = window.setTimeout(() => {
      setMirrorInactivityLevel('dimmed');
    }, mirrorModeConfig.dimTimeoutMs);

    inactivitySleepTimerRef.current = window.setTimeout(() => {
      setActiveView('home');
      setMirrorInactivityLevel('sleep');
    }, mirrorModeConfig.sleepTimeoutMs);
  }, [clearMirrorInactivityTimers, isMirrorMode]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setNow(new Date());
    }, 1000);

    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!isMirrorMode) {
      setMirrorStartupVisible(false);
      return;
    }

    setMirrorStartupVisible(true);

    const timer = window.setTimeout(() => {
      setMirrorStartupVisible(false);
    }, mirrorModeConfig.startupMs);

    return () => window.clearTimeout(timer);
  }, [isMirrorMode]);

  useEffect(() => {
    if (!isMirrorMode) {
      return;
    }

    const timer = window.setInterval(() => {
      setBurnInIndex((current) => (current + 1) % burnInOffsets.length);
    }, mirrorModeConfig.burnInShiftMs);

    return () => window.clearInterval(timer);
  }, [isMirrorMode]);

  useEffect(() => {
    if (!isMirrorMode) {
      clearMirrorInactivityTimers();
      setMirrorInactivityLevel('active');
      return;
    }

    const activityEvents = [
      'click',
      'keydown',
      'mousemove',
      'pointerdown',
      'touchstart',
      'wheel',
    ] as const;

    activityEvents.forEach((eventName) => {
      window.addEventListener(eventName, registerMirrorActivity, {
        passive: true,
      });
    });
    registerMirrorActivity();

    return () => {
      activityEvents.forEach((eventName) => {
        window.removeEventListener(eventName, registerMirrorActivity);
      });
      clearMirrorInactivityTimers();
    };
  }, [clearMirrorInactivityTimers, isMirrorMode, registerMirrorActivity]);

  useEffect(() => {
    setVoiceSupported(getSpeechRecognitionConstructor() !== null);

    return () => {
      recognitionRef.current?.abort();
    };
  }, []);

  useEffect(() => {
    if (
      !('speechSynthesis' in window) ||
      typeof SpeechSynthesisUtterance === 'undefined'
    ) {
      setTtsSupported(false);
      return;
    }

    const synthesis = window.speechSynthesis;

    function loadSpeechVoices() {
      const availableVoices = synthesis.getVoices();

      ttsVoicesRef.current = availableVoices;
      setTtsVoices(availableVoices);
    }

    ttsSupportedRef.current = true;
    setTtsSupported(true);
    loadSpeechVoices();
    synthesis.addEventListener('voiceschanged', loadSpeechVoices);

    return () => {
      speechRequestRef.current += 1;
      synthesis.cancel();
      synthesis.removeEventListener('voiceschanged', loadSpeechVoices);
    };
  }, []);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setActiveView('home');
      }
    }

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  useEffect(() => {
    let isActive = true;

    async function loadBackendStatus() {
      try {
        const [health, system, voice, currentWeather] = await Promise.all([
          getHealthStatus(),
          getSystemStatus(),
          getVoiceStatus(),
          getWeather(),
        ]);

        if (!isActive) {
          return;
        }

        setHealthStatus(health);
        setSystemStatus(system);
        setVoiceStatus(voice);
        setWeather(currentWeather);
        setBackendState({ error: null, isLoading: false });
      } catch {
        if (!isActive) {
          return;
        }

        setBackendState({
          error: 'Backend unavailable',
          isLoading: false,
        });
      }
    }

    loadBackendStatus();

    return () => {
      isActive = false;
    };
  }, []);

  useEffect(() => {
    let isActive = true;

    async function loadSpotify() {
      try {
        const [status, playback] = await Promise.all([
          getSpotifyStatus(),
          getSpotifyPlayback(),
        ]);

        if (!isActive) {
          return;
        }

        setSpotifyStatus(status);
        setSpotifyPlayback(playback);
        setSpotifyState({
          actionMessage: null,
          error: null,
          isLoading: false,
        });
      } catch {
        if (!isActive) {
          return;
        }

        setSpotifyState({
          actionMessage: null,
          error: 'Spotify API unavailable',
          isLoading: false,
        });
      }
    }

    loadSpotify();

    return () => {
      isActive = false;
    };
  }, []);

  useEffect(() => {
    let isActive = true;

    async function loadCalendar() {
      try {
        const [status, today, upcoming] = await Promise.all([
          getCalendarStatus(),
          getCalendarToday(),
          getCalendarUpcoming(),
        ]);

        if (!isActive) {
          return;
        }

        setCalendarStatus(status);
        setCalendarToday(today);
        setCalendarUpcoming(upcoming);
        setCalendarState({
          error: null,
          isLoading: false,
        });
      } catch {
        if (!isActive) {
          return;
        }

        setCalendarState({
          error: 'Calendar API unavailable',
          isLoading: false,
        });
      }
    }

    loadCalendar();

    return () => {
      isActive = false;
    };
  }, []);

  useEffect(() => {
    let isActive = true;

    async function loadContext() {
      try {
        const context = await getDailyContext();

        if (!isActive) {
          return;
        }

        setDailyContext(context);
        setContextState({
          error: null,
          isLoading: false,
        });
      } catch {
        if (!isActive) {
          return;
        }

        setContextState({
          error: 'Context API unavailable',
          isLoading: false,
        });
      }
    }

    loadContext();

    return () => {
      isActive = false;
    };
  }, []);

  useEffect(() => {
    let isActive = true;

    async function loadProactiveSummary() {
      try {
        const summary = await getProactiveSummary();

        if (!isActive) {
          return;
        }

        setProactiveSummary(summary);
        setProactiveState({
          error: null,
          isLoading: false,
        });
      } catch {
        if (!isActive) {
          return;
        }

        setProactiveState({
          error: 'Proactive summary unavailable',
          isLoading: false,
        });
      }
    }

    loadProactiveSummary();

    return () => {
      isActive = false;
    };
  }, []);

  const currentTime = useMemo(
    () =>
      new Intl.DateTimeFormat('en-GB', {
        hour: '2-digit',
        minute: '2-digit',
      }).format(now),
    [now],
  );

  const currentDate = useMemo(
    () =>
      new Intl.DateTimeFormat('en-GB', {
        weekday: 'long',
        day: 'numeric',
        month: 'long',
        year: 'numeric',
      }).format(now),
    [now],
  );

  const backendLabel = useMemo(() => {
    if (backendState.isLoading) {
      return 'Checking backend';
    }

    if (backendState.error) {
      return 'Backend offline';
    }

    return `Backend ${formatStatus(healthStatus?.status)}`;
  }, [backendState.error, backendState.isLoading, healthStatus]);

  const weatherSummary = useMemo(() => {
    if (backendState.isLoading) {
      return 'Reading weather';
    }

    if (backendState.error || !weather || weather.status !== 'online') {
      return 'Weather unavailable';
    }

    return `${weather.condition}. ${weather.location}.`;
  }, [backendState.error, backendState.isLoading, weather]);

  const calendarSummary = useMemo(() => {
    if (calendarState.isLoading) {
      return 'Checking schedule';
    }

    if (calendarState.error) {
      return 'Calendar unavailable';
    }

    if (!calendarStatus?.configured) {
      return 'Setup needed';
    }

    if (!calendarStatus.authenticated) {
      return 'Connect Google Calendar';
    }

    const eventCount = calendarToday?.events.length ?? 0;
    if (eventCount === 0) {
      return 'No events today';
    }

    return `${eventCount} event${eventCount === 1 ? '' : 's'} today`;
  }, [
    calendarState.error,
    calendarState.isLoading,
    calendarStatus,
    calendarToday,
  ]);

  const contextSummary = useMemo(() => {
    if (contextState.isLoading) {
      return 'Building daily context';
    }

    if (contextState.error || !dailyContext) {
      return 'Context unavailable';
    }

    const suggestion = dailyContext.suggested_focus[0];
    if (suggestion) {
      return suggestion.title;
    }

    return dailyContext.message;
  }, [contextState.error, contextState.isLoading, dailyContext]);

  const proactiveNudge = useMemo(() => {
    if (proactiveState.isLoading) {
      return 'Reading the day';
    }

    if (proactiveState.error || !proactiveSummary) {
      return contextSummary;
    }

    if (proactiveSummary.priority === 'none') {
      return proactiveSummary.message;
    }

    return `${proactiveSummary.headline}. ${proactiveSummary.message}`;
  }, [
    contextSummary,
    proactiveState.error,
    proactiveState.isLoading,
    proactiveSummary,
  ]);

  const voiceLabel = voiceListening
    ? 'Listening now'
    : voiceSupported
      ? 'Voice ready'
      : voiceStatus?.listening
        ? 'Listening'
        : 'Voice planned';
  const systemLabel = backendState.error
    ? 'System offline'
    : formatStatus(systemStatus?.status);
  const assistantOrbState: AssistantOrbState = voiceListening
    ? 'listening'
    : assistantBusy
      ? 'thinking'
      : ttsSpeaking
        ? 'speaking'
        : assistantError || voiceError || backendState.error
          ? 'error'
          : 'idle';
  const burnInOffset = burnInOffsets[burnInIndex] ?? burnInOffsets[0];
  const mirrorStartupChecks = useMemo<MirrorStartupCheck[]>(
    () => [
      {
        label: 'Backend',
        status: backendLabel,
        tone: backendState.isLoading
          ? 'checking'
          : backendState.error
            ? 'offline'
            : 'online',
      },
      {
        label: 'Weather',
        status: weatherSummary,
        tone: backendState.isLoading
          ? 'checking'
          : weather?.status === 'online'
            ? 'online'
            : 'offline',
      },
      {
        label: 'Voice',
        status: voiceLabel,
        tone: voiceSupported || voiceStatus?.listening ? 'online' : 'planned',
      },
      {
        label: 'Calendar',
        status: calendarSummary,
        tone: calendarState.isLoading
          ? 'checking'
          : calendarState.error || !calendarStatus?.configured
            ? 'planned'
            : calendarStatus.authenticated
              ? 'online'
              : 'planned',
      },
      {
        label: 'Context',
        status: contextSummary,
        tone: contextState.isLoading
          ? 'checking'
          : contextState.error
            ? 'offline'
            : 'online',
      },
      {
        label: 'Proactive',
        status: proactiveNudge,
        tone: proactiveState.isLoading
          ? 'checking'
          : proactiveState.error
            ? 'planned'
            : 'online',
      },
    ],
    [
      backendLabel,
      backendState.error,
      backendState.isLoading,
      calendarState.error,
      calendarState.isLoading,
      calendarStatus,
      calendarSummary,
      contextState.error,
      contextState.isLoading,
      contextSummary,
      proactiveNudge,
      proactiveState.error,
      proactiveState.isLoading,
      voiceLabel,
      voiceStatus,
      voiceSupported,
      weather,
      weatherSummary,
    ],
  );

  function performUiAction(action: AssistantUiAction) {
    registerMirrorActivity();

    if (action.type === 'open_focus_view') {
      setActiveView(action.target);
    }
  }

  async function handleAssistantCommand(
    message: string,
    source: 'typed' | 'voice',
    command: AssistantCommandRoute,
  ) {
    setAssistantError(null);
    setDraft('');
    performUiAction(command.action);
    setAssistantMessages((messages) => [
      ...messages,
      {
        role: 'user',
        text: message,
        meta: source === 'voice' ? 'Voice transcript' : undefined,
      },
    ]);

    if (command.intent === 'daily_context') {
      setAssistantBusy(true);

      try {
        const [context, result] = await Promise.all([
          getDailyContext(),
          sendAssistantMessage(message),
        ]);

        setDailyContext(context);
        setContextState({
          error: null,
          isLoading: false,
        });
        setAssistantProvider(result.provider);
        setAssistantMessages((messages) => [
          ...messages,
          {
            role: 'assistant',
            text: result.reply,
            meta: `Context / ${formatStatus(result.context_action ?? command.intent)}`,
          },
        ]);
        speakText(result.reply);
      } catch {
        const fallback =
          'Daily context is unavailable right now. Check the backend context route.';
        setContextState({
          error: 'Context API unavailable',
          isLoading: false,
        });
        setAssistantMessages((messages) => [
          ...messages,
          {
            role: 'assistant',
            text: fallback,
            meta: 'Context fallback',
          },
        ]);
        speakText(fallback);
      } finally {
        setAssistantBusy(false);
      }

      return;
    }

    if (command.intent === 'calendar_today') {
      setAssistantBusy(true);

      try {
        const [status, today, upcoming] = await Promise.all([
          getCalendarStatus(),
          getCalendarToday(),
          getCalendarUpcoming(),
        ]);
        const response = summarizeCalendarToday(today, status);

        setCalendarStatus(status);
        setCalendarToday(today);
        setCalendarUpcoming(upcoming);
        setCalendarState({
          error: null,
          isLoading: false,
        });
        setAssistantMessages((messages) => [
          ...messages,
          {
            role: 'assistant',
            text: response,
            meta: `UI action / ${formatStatus(command.intent)}`,
          },
        ]);
        speakText(response);
      } catch {
        const fallback =
          'Calendar is unavailable right now. Check the backend and Google Calendar setup.';
        setCalendarState({
          error: 'Calendar API unavailable',
          isLoading: false,
        });
        setAssistantMessages((messages) => [
          ...messages,
          {
            role: 'assistant',
            text: fallback,
            meta: 'Calendar fallback',
          },
        ]);
        speakText(fallback);
      } finally {
        setAssistantBusy(false);
      }

      return;
    }

    setAssistantMessages((messages) => [
      ...messages,
      {
        role: 'assistant',
        text: command.response,
        meta: `UI action / ${formatStatus(command.intent)}`,
      },
    ]);
    speakText(command.response);
  }

  async function sendAssistantRequest(
    message: string,
    source: 'typed' | 'voice',
  ) {
    if (!message || assistantBusy) {
      return;
    }

    const command = routeAssistantCommand(message);
    if (command) {
      await handleAssistantCommand(message, source, command);
      return;
    }

    setAssistantBusy(true);
    setAssistantError(null);
    setAssistantMessages((messages) => [
      ...messages,
      {
        role: 'user',
        text: message,
        meta: source === 'voice' ? 'Voice transcript' : undefined,
      },
    ]);

    try {
      const result: AssistantReply = await sendAssistantMessage(message);
      setAssistantProvider(result.provider);
      setAssistantMessages((messages) => [
        ...messages,
        {
          role: 'assistant',
          text: result.reply,
          meta: `${result.provider}${result.model ? ` / ${result.model}` : ''}`,
        },
      ]);
      speakText(result.reply);
      setDraft('');
    } catch {
      setAssistantError(
        'Assistant unavailable. Check the backend or provider.',
      );
      setAssistantMessages((messages) => [
        ...messages,
        {
          role: 'assistant',
          text: 'Assistant request failed. The UI is still working, but the route or provider did not answer.',
          meta: 'Fallback state',
        },
      ]);
    } finally {
      setAssistantBusy(false);
    }
  }

  function stopSpeech() {
    speechRequestRef.current += 1;
    window.speechSynthesis?.cancel();
    setTtsSpeaking(false);
  }

  function speakText(text: string) {
    if (!ttsSupportedRef.current || ttsMutedRef.current || !text.trim()) {
      return;
    }

    const synthesis = window.speechSynthesis;
    const selectedVoice =
      ttsVoicesRef.current.find(
        (voice) => voice.voiceURI === ttsVoiceURIRef.current,
      ) ?? null;
    const requestId = speechRequestRef.current + 1;

    speechRequestRef.current = requestId;
    synthesis.cancel();
    setTtsSpeaking(false);

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.96;
    utterance.pitch = 1;

    if (selectedVoice) {
      utterance.voice = selectedVoice;
    }

    utterance.onstart = () => {
      if (speechRequestRef.current === requestId) {
        setTtsSpeaking(true);
      }
    };

    utterance.onend = () => {
      if (speechRequestRef.current === requestId) {
        setTtsSpeaking(false);
      }
    };

    utterance.onerror = () => {
      if (speechRequestRef.current === requestId) {
        setTtsSpeaking(false);
      }
    };

    synthesis.speak(utterance);
  }

  function handleTtsMutedChange(nextValue: boolean) {
    ttsMutedRef.current = nextValue;
    setTtsMuted(nextValue);

    if (nextValue) {
      stopSpeech();
    }
  }

  function handleTtsVoiceChange(value: string) {
    ttsVoiceURIRef.current = value;
    setTtsVoiceURI(value);
  }

  function testSpeechOutput() {
    speakText('Mirrage voice output is ready.');
  }

  async function handleAssistantSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    await sendAssistantRequest(draft.trim(), 'typed');
  }

  async function requestMicrophoneAccess() {
    if (!navigator.mediaDevices?.getUserMedia) {
      throw new Error('Browser microphone access is unavailable.');
    }

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    stream.getTracks().forEach((track) => track.stop());
    setMicrophoneReady(true);
  }

  async function startVoiceCapture() {
    registerMirrorActivity();

    if (assistantBusy || voiceListening) {
      return;
    }

    const SpeechRecognition = getSpeechRecognitionConstructor();
    if (!SpeechRecognition) {
      setVoiceError('Speech recognition is not supported in this browser.');
      return;
    }

    setVoiceError(null);
    setVoiceTranscript('');
    setVoiceInterimTranscript('');

    try {
      await requestMicrophoneAccess();

      let capturedTranscript = '';
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = 'en-GB';

      recognition.onresult = (event) => {
        const finalParts: string[] = [];
        const interimParts: string[] = [];

        for (let index = 0; index < event.results.length; index += 1) {
          const result = event.results[index];
          const transcript = result?.[0]?.transcript.trim();

          if (!result || !transcript) {
            continue;
          }

          if (result.isFinal) {
            finalParts.push(transcript);
          } else {
            interimParts.push(transcript);
          }
        }

        capturedTranscript = [...finalParts, ...interimParts].join(' ').trim();
        setVoiceTranscript(finalParts.join(' ').trim() || capturedTranscript);
        setVoiceInterimTranscript(interimParts.join(' ').trim());
      };

      recognition.onerror = (event) => {
        setVoiceError(getVoiceErrorMessage(event.error));
        setVoiceListening(false);
      };

      recognition.onend = () => {
        setVoiceListening(false);
        recognitionRef.current = null;
        setVoiceInterimTranscript('');

        if (capturedTranscript) {
          void sendAssistantRequest(capturedTranscript, 'voice');
          return;
        }

        setVoiceError((currentError) => currentError ?? 'No speech was heard.');
      };

      recognitionRef.current = recognition;
      setVoiceListening(true);
      recognition.start();
    } catch (error) {
      setVoiceListening(false);
      recognitionRef.current = null;
      setVoiceError(
        error instanceof Error
          ? error.message
          : 'Microphone access could not be started.',
      );
    }
  }

  function stopVoiceCapture() {
    registerMirrorActivity();
    recognitionRef.current?.stop();
  }

  function openFocus(view: Exclude<FocusView, 'home'>) {
    registerMirrorActivity();
    setActiveView(view);
  }

  function closeFocus() {
    registerMirrorActivity();
    setActiveView('home');
  }

  async function refreshSpotify() {
    registerMirrorActivity();

    setSpotifyState((current) => ({
      ...current,
      error: null,
      isLoading: true,
    }));

    try {
      const [status, playback] = await Promise.all([
        getSpotifyStatus(),
        getSpotifyPlayback(),
      ]);
      setSpotifyStatus(status);
      setSpotifyPlayback(playback);
      setSpotifyState((current) => ({
        ...current,
        error: null,
        isLoading: false,
      }));
    } catch {
      setSpotifyState((current) => ({
        ...current,
        error: 'Spotify API unavailable',
        isLoading: false,
      }));
    }
  }

  async function refreshCalendar() {
    registerMirrorActivity();

    setCalendarState({
      error: null,
      isLoading: true,
    });

    try {
      const [status, today, upcoming] = await Promise.all([
        getCalendarStatus(),
        getCalendarToday(),
        getCalendarUpcoming(),
      ]);
      setCalendarStatus(status);
      setCalendarToday(today);
      setCalendarUpcoming(upcoming);
      setCalendarState({
        error: null,
        isLoading: false,
      });
    } catch {
      setCalendarState({
        error: 'Calendar API unavailable',
        isLoading: false,
      });
    }
  }

  async function refreshContext() {
    registerMirrorActivity();

    setContextState({
      error: null,
      isLoading: true,
    });

    try {
      const context = await getDailyContext();
      setDailyContext(context);
      setContextState({
        error: null,
        isLoading: false,
      });
      return context;
    } catch {
      setContextState({
        error: 'Context API unavailable',
        isLoading: false,
      });
      return null;
    }
  }

  async function handleSpotifyAction(
    action: 'play' | 'pause' | 'next' | 'previous',
  ) {
    registerMirrorActivity();

    setSpotifyState((current) => ({
      ...current,
      actionMessage: null,
      error: null,
      isLoading: true,
    }));

    try {
      const result = await runSpotifyAction(action);
      await refreshSpotify();
      setSpotifyState((current) => ({
        ...current,
        actionMessage: result.message,
        error: null,
        isLoading: false,
      }));
    } catch {
      setSpotifyState({
        actionMessage: null,
        error: 'Spotify control failed. Check account, device, and playback.',
        isLoading: false,
      });
    }
  }

  return (
    <main
      className={`relative mx-auto flex min-h-screen flex-col overflow-hidden ${
        isMirrorMode
          ? 'mirror-mode w-full max-w-none justify-stretch px-6 py-6 md:px-10 md:py-8'
          : 'w-[min(1180px,100%)] justify-center px-4 py-8 md:px-8'
      }`}
    >
      <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(circle_at_20%_20%,rgba(109,215,232,0.10),transparent_28%),radial-gradient(circle_at_85%_70%,rgba(122,217,165,0.08),transparent_28%)]" />

      <section
        className={`transition-all duration-500 ${
          activeView === 'home'
            ? 'translate-y-0 opacity-100'
            : 'pointer-events-none -translate-y-4 opacity-0 blur-sm'
        }`}
        aria-hidden={activeView !== 'home'}
      >
        {isMirrorMode ? (
          <MirrorHomeState
            assistantOrbState={assistantOrbState}
            backendLabel={backendLabel}
            burnInOffset={burnInOffset}
            calendarSummary={calendarSummary}
            currentDate={currentDate}
            currentTime={currentTime}
            inactivityLevel={mirrorInactivityLevel}
            onOpen={openFocus}
            proactiveNudge={proactiveNudge}
            proactiveSummary={proactiveSummary}
            voiceLabel={voiceLabel}
            weather={weather}
            weatherSummary={weatherSummary}
          />
        ) : (
          <HomeState
            backendLabel={backendLabel}
            calendarSummary={calendarSummary}
            contextSummary={contextSummary}
            currentDate={currentDate}
            currentTime={currentTime}
            onOpen={openFocus}
            systemLabel={systemLabel}
            voiceLabel={voiceLabel}
            weather={weather}
            weatherSummary={weatherSummary}
          />
        )}
      </section>

      <section
        className={`absolute inset-x-4 top-8 transition-all duration-500 md:inset-x-8 md:top-10 ${
          activeView === 'home'
            ? 'pointer-events-none translate-y-8 opacity-0 blur-sm'
            : 'translate-y-0 opacity-100'
        }`}
        aria-hidden={activeView === 'home'}
      >
        {activeView === 'weather' && (
          <WeatherFocus
            backendState={backendState}
            onClose={closeFocus}
            weather={weather}
          />
        )}

        {activeView === 'assistant' && (
          <AssistantFocus
            assistantOrbState={assistantOrbState}
            assistantBusy={assistantBusy}
            assistantError={assistantError}
            assistantMessages={assistantMessages}
            assistantProvider={assistantProvider}
            draft={draft}
            isMirrorMode={isMirrorMode}
            microphoneReady={microphoneReady}
            onClose={closeFocus}
            onDraftChange={setDraft}
            onStartVoice={startVoiceCapture}
            onStopVoice={stopVoiceCapture}
            onSubmit={handleAssistantSubmit}
            onStopSpeech={stopSpeech}
            onTestSpeech={testSpeechOutput}
            onTtsMutedChange={handleTtsMutedChange}
            onTtsVoiceChange={handleTtsVoiceChange}
            ttsMuted={ttsMuted}
            ttsSpeaking={ttsSpeaking}
            ttsSupported={ttsSupported}
            ttsVoiceURI={ttsVoiceURI}
            ttsVoices={ttsVoices}
            voiceError={voiceError}
            voiceInterimTranscript={voiceInterimTranscript}
            voiceListening={voiceListening}
            voiceSupported={voiceSupported}
            voiceTranscript={voiceTranscript}
          />
        )}

        {activeView === 'media' && (
          <MediaFocus
            loginUrl={getSpotifyLoginUrl()}
            onClose={closeFocus}
            onRefresh={() => void refreshSpotify()}
            onSpotifyAction={(action) => void handleSpotifyAction(action)}
            spotifyPlayback={spotifyPlayback}
            spotifyState={spotifyState}
            spotifyStatus={spotifyStatus}
          />
        )}

        {activeView === 'calendar' && (
          <CalendarFocus
            calendarState={calendarState}
            calendarStatus={calendarStatus}
            loginUrl={getCalendarLoginUrl()}
            onClose={closeFocus}
            onRefresh={() => void refreshCalendar()}
            today={calendarToday}
            upcoming={calendarUpcoming}
          />
        )}

        {activeView === 'context' && (
          <ContextFocus
            context={dailyContext}
            contextState={contextState}
            onClose={closeFocus}
            onRefresh={() => void refreshContext()}
            proactiveSummary={proactiveSummary}
          />
        )}
      </section>
      {isMirrorMode && (
        <>
          <MirrorDimmingOverlay level={mirrorInactivityLevel} />
          {mirrorStartupVisible && (
            <MirrorStartup checks={mirrorStartupChecks} />
          )}
        </>
      )}
    </main>
  );
}

interface HomeStateProps {
  backendLabel: string;
  calendarSummary: string;
  contextSummary: string;
  currentDate: string;
  currentTime: string;
  onOpen: (view: Exclude<FocusView, 'home'>) => void;
  systemLabel: string;
  voiceLabel: string;
  weather: WeatherInfo | null;
  weatherSummary: string;
}

function HomeState({
  backendLabel,
  calendarSummary,
  contextSummary,
  currentDate,
  currentTime,
  onOpen,
  systemLabel,
  voiceLabel,
  weather,
  weatherSummary,
}: HomeStateProps) {
  return (
    <div className="grid min-h-[82vh] content-between gap-10">
      <header className="flex items-start justify-between gap-6">
        <div>
          <p className={labelClass}>Mirrage</p>
          <h1 className="mt-4 text-[4.5rem] font-semibold leading-none tracking-normal text-text sm:text-[7rem] md:text-[9rem]">
            {currentTime}
          </h1>
          <p className="mt-4 text-lg text-muted">{currentDate}</p>
        </div>

        <div className="hidden rounded-full border border-line bg-panel px-4 py-2 text-sm text-muted shadow-mirror md:block">
          {backendLabel}
        </div>
      </header>

      <section
        className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-5"
        aria-label="Ambient focus controls"
      >
        <button
          type="button"
          className={focusButtonBase}
          onClick={() => onOpen('weather')}
        >
          <span className={labelClass}>Weather</span>
          <strong className="mt-8 block text-4xl font-semibold text-amber">
            {formatTemperature(weather)}
          </strong>
          <p className={`mt-3 ${mutedClass}`}>{weatherSummary}</p>
        </button>

        <button
          type="button"
          className={focusButtonBase}
          onClick={() => onOpen('assistant')}
        >
          <span className={labelClass}>Assistant</span>
          <strong className="mt-8 block text-4xl font-semibold text-green">
            Ready
          </strong>
          <p className={`mt-3 ${mutedClass}`}>
            Open a focused assistant view and type or speak a request.
          </p>
        </button>

        <button
          type="button"
          className={focusButtonBase}
          onClick={() => onOpen('media')}
        >
          <span className={labelClass}>Media</span>
          <strong className="mt-8 block text-4xl font-semibold text-text">
            Spotify
          </strong>
          <p className={`mt-3 ${mutedClass}`}>
            Connect an account to show playback and mirror controls.
          </p>
        </button>

        <button
          type="button"
          className={focusButtonBase}
          onClick={() => onOpen('calendar')}
        >
          <span className={labelClass}>Calendar</span>
          <strong className="mt-8 block text-4xl font-semibold text-cyan">
            Today
          </strong>
          <p className={`mt-3 ${mutedClass}`}>{calendarSummary}</p>
        </button>

        <button
          type="button"
          className={focusButtonBase}
          onClick={() => onOpen('context')}
        >
          <span className={labelClass}>Context</span>
          <strong className="mt-8 block text-4xl font-semibold text-green">
            Daily
          </strong>
          <p className={`mt-3 ${mutedClass}`}>{contextSummary}</p>
        </button>
      </section>

      <footer className="grid gap-3 text-sm text-muted md:grid-cols-3">
        <p>{systemLabel}</p>
        <p>{voiceLabel}</p>
        <p>Hardware planning only</p>
      </footer>
    </div>
  );
}

interface MirrorHomeStateProps {
  assistantOrbState: AssistantOrbState;
  backendLabel: string;
  burnInOffset: BurnInOffset;
  calendarSummary: string;
  currentDate: string;
  currentTime: string;
  inactivityLevel: MirrorInactivityLevel;
  onOpen: (view: Exclude<FocusView, 'home'>) => void;
  proactiveNudge: string;
  proactiveSummary: ProactiveSummary | null;
  voiceLabel: string;
  weather: WeatherInfo | null;
  weatherSummary: string;
}

function MirrorHomeState({
  assistantOrbState,
  backendLabel,
  burnInOffset,
  calendarSummary,
  currentDate,
  currentTime,
  inactivityLevel,
  onOpen,
  proactiveNudge,
  proactiveSummary,
  voiceLabel,
  weather,
  weatherSummary,
}: MirrorHomeStateProps) {
  const transform = `translate(${burnInOffset.x}px, ${burnInOffset.y}px)`;

  return (
    <div
      className={`mirror-home ${inactivityLevel === 'sleep' ? 'mirror-home-sleep' : ''}`}
    >
      <div className="mirror-clock mirror-burn" style={{ transform }}>
        <p className={labelClass}>Mirrage</p>
        <h1>{currentTime}</h1>
        <p>{currentDate}</p>
      </div>

      <button
        type="button"
        className="mirror-weather mirror-burn"
        style={{ transform }}
        onClick={() => onOpen('weather')}
        aria-label="Open weather focus"
      >
        <span className={labelClass}>Weather</span>
        <strong>{formatTemperature(weather)}</strong>
        <span>{weatherSummary}</span>
      </button>

      <div className="mirror-orb-zone">
        <button
          type="button"
          className={`assistant-orb assistant-orb-${assistantOrbState} mirror-burn`}
          style={{ transform }}
          onClick={() => onOpen('assistant')}
          aria-label="Open assistant focus"
        >
          <span>{formatStatus(assistantOrbState)}</span>
        </button>
      </div>

      <div className="mirror-status mirror-burn" style={{ transform }}>
        <span
          className={`mirror-status-dot ${
            backendLabel.toLowerCase().includes('offline')
              ? 'mirror-status-dot-warn'
              : ''
          }`}
        />
        <span>{backendLabel}</span>
        <span>{voiceLabel}</span>
      </div>

      <nav className="mirror-focus-rail" aria-label="Mirror focus views">
        <button type="button" onClick={() => onOpen('context')}>
          Context
        </button>
        <button type="button" onClick={() => onOpen('calendar')}>
          Calendar
        </button>
        <button type="button" onClick={() => onOpen('media')}>
          Media
        </button>
      </nav>

      <div className="mirror-context-peek" aria-hidden="true">
        <span>{proactiveNudge}</span>
        {proactiveSummary && (
          <span
            className={`mirror-priority mirror-priority-${proactiveSummary.priority}`}
          >
            {formatStatus(proactiveSummary.priority)}
          </span>
        )}
        <span>{calendarSummary}</span>
      </div>
    </div>
  );
}

function MirrorDimmingOverlay({ level }: { level: MirrorInactivityLevel }) {
  return <div className={`mirror-dim-overlay mirror-dim-${level}`} />;
}

function MirrorStartup({ checks }: { checks: MirrorStartupCheck[] }) {
  return (
    <div className="mirror-startup" role="status" aria-live="polite">
      <div>
        <p className={labelClass}>Mirrage</p>
        <h2>Starting mirror mode</h2>
        <div className="mirror-startup-checks">
          {checks.map((check) => (
            <div className="mirror-startup-check" key={check.label}>
              <span
                className={`mirror-startup-dot mirror-startup-dot-${check.tone}`}
              />
              <span>{check.label}</span>
              <strong>{check.status}</strong>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

interface WeatherFocusProps {
  backendState: BackendState;
  onClose: () => void;
  weather: WeatherInfo | null;
}

function WeatherFocus({ backendState, onClose, weather }: WeatherFocusProps) {
  const weatherOnline = !backendState.error && weather?.status === 'online';

  return (
    <div className={focusPanelClass}>
      <FocusHeader
        eyebrow="Weather Focus"
        onClose={onClose}
        title={weatherOnline ? weather.location : 'Weather unavailable'}
      />

      <div className="mt-12 grid gap-8 md:grid-cols-[1.2fr_0.8fr]">
        <div>
          <p className="text-[5rem] font-semibold leading-none text-amber md:text-[8rem]">
            {formatTemperature(weather)}
          </p>
          <p className="mt-5 text-2xl text-text">
            {weatherOnline
              ? weather.condition
              : 'Weather data is not available right now.'}
          </p>
        </div>

        <div className="grid content-end gap-4 rounded-lg border border-line bg-page/50 p-5">
          <div>
            <p className={labelClass}>Source</p>
            <p className="mt-2 text-lg text-text">Open-Meteo via backend</p>
          </div>
          <div>
            <p className={labelClass}>Updated</p>
            <p className="mt-2 text-lg text-text">
              {formatUpdated(weather?.updated)}
            </p>
          </div>
          <div>
            <p className={labelClass}>Fallback</p>
            <p className={`mt-2 ${mutedClass}`}>
              If the provider fails, the UI stays readable and reports the
              missing data.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

interface ContextFocusProps {
  context: DailyContext | null;
  contextState: ContextUiState;
  onClose: () => void;
  onRefresh: () => void;
  proactiveSummary: ProactiveSummary | null;
}

function ContextFocus({
  context,
  contextState,
  onClose,
  onRefresh,
  proactiveSummary,
}: ContextFocusProps) {
  const suggestions = context?.suggested_focus ?? [];
  const goals = context?.memory.goals ?? [];
  const routines = context?.memory.routines ?? [];
  const preferences = context?.memory.preferences ?? [];
  const todayEvents = context?.calendar.today_events ?? [];

  return (
    <div className={focusPanelClass}>
      <FocusHeader
        eyebrow="Daily Context"
        onClose={onClose}
        title={context ? 'Today' : 'Context unavailable'}
      />

      <div className="mt-8 flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={onRefresh}
          disabled={contextState.isLoading}
          className="rounded-lg border border-cyan/50 bg-cyan/10 px-4 py-3 text-sm font-semibold text-cyan transition hover:bg-cyan/15 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {contextState.isLoading ? 'Refreshing...' : 'Refresh context'}
        </button>
        <p className="text-sm text-muted">
          {context?.message ??
            'Context loads from backend weather, calendar, and local memory.'}
        </p>
      </div>

      {contextState.error && (
        <p className="mt-4 rounded-md border border-amber/40 bg-amber/10 p-3 text-sm text-amber">
          {contextState.error}
        </p>
      )}

      {proactiveSummary && (
        <div className="ambient-proactive-briefing">
          <p className={labelClass}>
            Proactive {formatStatus(proactiveSummary.priority)}
          </p>
          <h2>{proactiveSummary.headline}</h2>
          <p>{proactiveSummary.message}</p>
        </div>
      )}

      <div className="mt-8 grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
        <section className="rounded-lg border border-line bg-page/40 p-5">
          <p className={labelClass}>Overview</p>
          <h2 className="mt-3 text-4xl font-semibold text-text">
            {context?.date ?? 'No daily context yet'}
          </h2>
          <p className="mt-4 text-lg leading-relaxed text-muted">
            {context
              ? `${context.weather.summary} ${context.calendar.message}`
              : 'Start the backend and refresh this view.'}
          </p>

          <div className="mt-6 grid gap-3 md:grid-cols-3">
            <ContextMetric
              label="Weather"
              value={formatStatus(context?.weather.status)}
            />
            <ContextMetric
              label="Calendar"
              value={`${context?.calendar.today_event_count ?? 0} today`}
            />
            <ContextMetric
              label="Memory"
              value={formatStatus(context?.memory.status)}
            />
          </div>

          <div className="mt-8">
            <p className={labelClass}>Suggested focus</p>
            <div className="mt-4 grid gap-3">
              {suggestions.map((suggestion) => (
                <article
                  className="rounded-lg border border-line bg-panel p-4"
                  key={`${suggestion.source}-${suggestion.title}`}
                >
                  <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                    <div>
                      <h3 className="text-2xl font-semibold text-text">
                        {suggestion.title}
                      </h3>
                      <p className="mt-2 text-sm leading-relaxed text-muted">
                        {suggestion.reason}
                      </p>
                    </div>
                    <p className="shrink-0 text-xs font-bold uppercase tracking-[0.18em] text-cyan">
                      {suggestion.priority}
                    </p>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        <aside className="grid gap-4">
          <section className="rounded-lg border border-line bg-page/40 p-5">
            <p className={labelClass}>Calendar</p>
            <p className="mt-2 text-sm text-muted">
              {context?.calendar.message ?? 'Calendar context is not loaded.'}
            </p>
            {todayEvents.length > 0 && (
              <CalendarEventList
                events={todayEvents.slice(0, 3)}
                mode="today"
              />
            )}
          </section>

          <section className="rounded-lg border border-line bg-page/40 p-5">
            <p className={labelClass}>Goals</p>
            <MemoryLineList
              emptyText="No local goals saved yet."
              items={goals}
            />
          </section>

          <section className="rounded-lg border border-line bg-page/40 p-5">
            <p className={labelClass}>Routines</p>
            <MemoryLineList
              emptyText="No routines saved yet."
              items={routines}
            />
          </section>

          <section className="rounded-lg border border-line bg-page/40 p-5">
            <p className={labelClass}>Preferences</p>
            <MemoryLineList
              emptyText="No preferences saved yet."
              items={preferences.slice(0, 3)}
            />
          </section>
        </aside>
      </div>
    </div>
  );
}

function ContextMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-line bg-panel p-4">
      <p className={labelClass}>{label}</p>
      <p className="mt-2 text-lg font-semibold text-text">{value}</p>
    </div>
  );
}

function MemoryLineList({
  emptyText,
  items,
}: {
  emptyText: string;
  items: DailyContext['memory']['goals'];
}) {
  if (items.length === 0) {
    return <p className="mt-3 text-sm text-muted">{emptyText}</p>;
  }

  return (
    <div className="mt-4 grid gap-3">
      {items.map((item) => (
        <div
          className="rounded-lg border border-line bg-panel p-4"
          key={item.id}
        >
          <p className="font-semibold text-text">
            {item.key.replace(/^goal: /, '')}
          </p>
          <p className="mt-2 text-sm leading-relaxed text-muted">
            {item.value}
          </p>
        </div>
      ))}
    </div>
  );
}

interface CalendarFocusProps {
  calendarState: CalendarUiState;
  calendarStatus: CalendarStatus | null;
  loginUrl: string;
  onClose: () => void;
  onRefresh: () => void;
  today: CalendarSchedule | null;
  upcoming: CalendarSchedule | null;
}

function CalendarFocus({
  calendarState,
  calendarStatus,
  loginUrl,
  onClose,
  onRefresh,
  today,
  upcoming,
}: CalendarFocusProps) {
  const isConfigured = calendarStatus?.configured ?? false;
  const isAuthenticated = calendarStatus?.authenticated ?? false;
  const todayEvents = today?.events ?? [];
  const upcomingEvents = upcoming?.events ?? [];
  const title = isAuthenticated
    ? 'Daily schedule'
    : isConfigured
      ? 'Connect Calendar'
      : 'Calendar setup';

  return (
    <div className={focusPanelClass}>
      <FocusHeader eyebrow="Calendar Focus" onClose={onClose} title={title} />

      <div className="mt-8 grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
        <section className="rounded-lg border border-line bg-page/40 p-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className={labelClass}>Today</p>
              <p className="mt-2 text-lg text-muted">
                {today?.date ?? 'Schedule not loaded'}
              </p>
            </div>
            <button
              type="button"
              onClick={onRefresh}
              disabled={calendarState.isLoading}
              className="rounded-lg border border-line bg-panel-strong px-4 py-2 text-sm font-semibold text-text transition hover:border-cyan/70 hover:text-cyan disabled:cursor-not-allowed disabled:opacity-50"
            >
              {calendarState.isLoading ? 'Refreshing' : 'Refresh'}
            </button>
          </div>

          {todayEvents.length > 0 ? (
            <CalendarEventList events={todayEvents} mode="today" />
          ) : (
            <div className="mt-8 rounded-lg border border-line bg-panel p-5">
              <p className="text-2xl font-semibold text-text">
                {isAuthenticated ? 'No events today' : 'Calendar not connected'}
              </p>
              <p className={`mt-3 ${mutedClass}`}>
                {isAuthenticated
                  ? 'Your daily schedule is clear.'
                  : (today?.message ??
                    'Connect Google Calendar to show your day here.')}
              </p>
            </div>
          )}
        </section>

        <aside className="grid gap-5">
          <div className="rounded-lg border border-line bg-page/40 p-5">
            <p className={labelClass}>Connection</p>
            <p className="mt-3 text-lg text-text">
              {calendarStatus?.message ?? 'Checking Google Calendar.'}
            </p>
            <p className="mt-2 text-sm text-muted">
              Calendar: {calendarStatus?.calendar_id ?? 'primary'}
            </p>

            <div className="mt-5 flex flex-wrap gap-3">
              {isConfigured && !isAuthenticated && (
                <a
                  href={loginUrl}
                  className="rounded-lg border border-green/50 bg-green/10 px-4 py-3 text-sm font-semibold text-green transition hover:bg-green/15"
                >
                  Connect Google Calendar
                </a>
              )}
              <button
                type="button"
                onClick={onRefresh}
                disabled={calendarState.isLoading}
                className="rounded-lg border border-line bg-panel-strong px-4 py-3 text-sm font-semibold text-text transition hover:border-cyan/70 hover:text-cyan disabled:cursor-not-allowed disabled:opacity-50"
              >
                Check status
              </button>
            </div>

            {calendarState.error && (
              <p className="mt-4 rounded-md border border-amber/40 bg-amber/10 p-3 text-sm text-amber">
                {calendarState.error}
              </p>
            )}
          </div>

          <div className="rounded-lg border border-line bg-page/40 p-5">
            <p className={labelClass}>Upcoming</p>
            <p className="mt-2 text-sm text-muted">
              {upcoming?.message ?? 'Next events appear after connection.'}
            </p>

            {upcomingEvents.length > 0 && (
              <CalendarEventList
                events={upcomingEvents.slice(0, 5)}
                mode="upcoming"
              />
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}

function CalendarEventList({
  events,
  mode,
}: {
  events: CalendarEvent[];
  mode: 'today' | 'upcoming';
}) {
  return (
    <div className="mt-6 grid gap-3">
      {events.map((event) => (
        <article
          className="rounded-lg border border-line bg-panel p-4"
          key={`${event.id}-${event.start}`}
        >
          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div>
              <p className={labelClass}>
                {mode === 'today'
                  ? formatCalendarEventTime(event)
                  : formatCalendarEventDateTime(event)}
              </p>
              <h2 className="mt-2 text-2xl font-semibold text-text">
                {event.title}
              </h2>
              {event.location && (
                <p className="mt-2 text-sm text-muted">{event.location}</p>
              )}
            </div>

            {event.html_link && (
              <a
                href={event.html_link}
                target="_blank"
                rel="noreferrer"
                className="shrink-0 rounded-lg border border-line bg-page/70 px-3 py-2 text-sm font-semibold text-muted transition hover:border-cyan/70 hover:text-cyan"
              >
                Open
              </a>
            )}
          </div>
        </article>
      ))}
    </div>
  );
}

interface AssistantFocusProps {
  assistantOrbState: AssistantOrbState;
  assistantBusy: boolean;
  assistantError: string | null;
  assistantMessages: AssistantMessage[];
  assistantProvider: string | null;
  draft: string;
  isMirrorMode: boolean;
  microphoneReady: boolean;
  onClose: () => void;
  onDraftChange: (value: string) => void;
  onStartVoice: () => void;
  onStopVoice: () => void;
  onStopSpeech: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onTestSpeech: () => void;
  onTtsMutedChange: (value: boolean) => void;
  onTtsVoiceChange: (value: string) => void;
  ttsMuted: boolean;
  ttsSpeaking: boolean;
  ttsSupported: boolean;
  ttsVoiceURI: string;
  ttsVoices: SpeechSynthesisVoice[];
  voiceError: string | null;
  voiceInterimTranscript: string;
  voiceListening: boolean;
  voiceSupported: boolean;
  voiceTranscript: string;
}

function AssistantFocus({
  assistantOrbState,
  assistantBusy,
  assistantError,
  assistantMessages,
  assistantProvider,
  draft,
  isMirrorMode,
  microphoneReady,
  onClose,
  onDraftChange,
  onStartVoice,
  onStopVoice,
  onStopSpeech,
  onSubmit,
  onTestSpeech,
  onTtsMutedChange,
  onTtsVoiceChange,
  ttsMuted,
  ttsSpeaking,
  ttsSupported,
  ttsVoiceURI,
  ttsVoices,
  voiceError,
  voiceInterimTranscript,
  voiceListening,
  voiceSupported,
  voiceTranscript,
}: AssistantFocusProps) {
  const voiceButtonLabel = voiceListening ? 'Stop listening' : 'Push to talk';
  const speechStatus = !ttsSupported
    ? 'Speech output is not supported in this browser.'
    : ttsMuted
      ? 'Speech output is muted.'
      : ttsSpeaking
        ? 'Speaking assistant response.'
        : 'Assistant replies will be spoken aloud.';
  const latestUserMessage = [...assistantMessages]
    .reverse()
    .find((message) => message.role === 'user');
  const latestAssistantMessage = [...assistantMessages]
    .reverse()
    .find((message) => message.role === 'assistant');

  if (isMirrorMode) {
    return (
      <div className={`${focusPanelClass} ambient-assistant-focus`}>
        <FocusHeader
          eyebrow="Assistant"
          onClose={onClose}
          title="Talk to Mirrage"
        />

        <div className="ambient-assistant-stage">
          <button
            type="button"
            className={`assistant-orb assistant-orb-${assistantOrbState} ambient-assistant-orb`}
            onClick={voiceListening ? onStopVoice : onStartVoice}
            disabled={!voiceSupported || assistantBusy}
            aria-label={voiceButtonLabel}
          >
            <span>{formatStatus(assistantOrbState)}</span>
          </button>

          <div className="ambient-transcript">
            <p className={labelClass}>Transcript</p>
            <p>
              {voiceTranscript ||
                voiceInterimTranscript ||
                latestUserMessage?.text ||
                'Press the orb or type below.'}
            </p>
          </div>

          <div className="ambient-reply">
            <p className={labelClass}>Mirrage</p>
            <p>{latestAssistantMessage?.text ?? 'Standing by.'}</p>
            {latestAssistantMessage?.meta && (
              <span>{latestAssistantMessage.meta}</span>
            )}
          </div>
        </div>

        <form onSubmit={onSubmit} className="ambient-assistant-input">
          <input
            type="text"
            value={draft}
            onChange={(event) => onDraftChange(event.target.value)}
            placeholder="Type quietly to Mirrage"
            aria-label="Message the assistant"
          />
          <button type="submit" disabled={assistantBusy}>
            {assistantBusy ? 'Sending' : 'Send'}
          </button>
        </form>

        <div className="ambient-assistant-tools">
          <button
            type="button"
            onClick={voiceListening ? onStopVoice : onStartVoice}
            disabled={!voiceSupported || assistantBusy}
          >
            {voiceButtonLabel}
          </button>
          <button
            type="button"
            onClick={() => onTtsMutedChange(!ttsMuted)}
            disabled={!ttsSupported}
          >
            {ttsMuted ? 'Unmute' : 'Mute'}
          </button>
          <button
            type="button"
            onClick={onStopSpeech}
            disabled={!ttsSupported || !ttsSpeaking}
          >
            Stop speech
          </button>
        </div>

        <p className="ambient-assistant-status">
          {voiceError ??
            assistantError ??
            (voiceSupported
              ? microphoneReady
                ? speechStatus
                : 'Microphone permission is requested on first use.'
              : 'Speech recognition is not supported in this browser.')}
        </p>
      </div>
    );
  }

  return (
    <div className={focusPanelClass}>
      <FocusHeader
        eyebrow="Assistant Focus"
        onClose={onClose}
        title="Ask Mirrage"
      />

      <div className="mt-8 grid gap-6 lg:grid-cols-[1fr_340px]">
        <div className="max-h-[52vh] overflow-y-auto rounded-lg border border-line bg-page/40 p-4">
          <div className="grid gap-4">
            {assistantMessages.map((message, index) => (
              <div
                className={`max-w-[86%] rounded-lg border border-line p-4 ${
                  message.role === 'user'
                    ? 'ml-auto bg-cyan/10'
                    : 'bg-panel-strong'
                }`}
                key={`${message.role}-${index}-${message.text}`}
              >
                <p className={labelClass}>
                  {message.role === 'user' ? 'You' : 'Mirrage'}
                </p>
                <p className="mt-2 leading-relaxed text-text">{message.text}</p>
                {message.meta && (
                  <p className="mt-3 text-xs text-muted">{message.meta}</p>
                )}
              </div>
            ))}
          </div>
        </div>

        <aside className="rounded-lg border border-line bg-page/40 p-5">
          <p className={labelClass}>Provider</p>
          <p className="mt-2 text-lg text-text">
            {assistantProvider ?? 'Waiting for first request'}
          </p>
          <p className={`mt-4 ${mutedClass}`}>
            Push-to-talk uses browser speech recognition, then sends the
            transcript through the existing assistant endpoint.
          </p>

          <div className="mt-5 rounded-lg border border-line bg-panel p-4">
            <p className={labelClass}>Voice input</p>
            <p className="mt-2 text-sm text-muted">
              {voiceSupported
                ? microphoneReady
                  ? 'Microphone permission granted for this browser session.'
                  : 'Browser support detected. Permission is requested on first use.'
                : 'Speech recognition is not supported in this browser.'}
            </p>
            <button
              type="button"
              onClick={voiceListening ? onStopVoice : onStartVoice}
              disabled={!voiceSupported || assistantBusy}
              className="mt-4 w-full rounded-lg border border-cyan/50 bg-cyan/10 px-4 py-3 font-semibold text-cyan transition hover:bg-cyan/15 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {voiceButtonLabel}
            </button>
          </div>

          {(voiceTranscript || voiceInterimTranscript) && (
            <div className="mt-4 rounded-lg border border-line bg-page/60 p-4">
              <p className={labelClass}>Transcript</p>
              <p className="mt-2 leading-relaxed text-text">
                {voiceTranscript || voiceInterimTranscript}
              </p>
              {voiceInterimTranscript && (
                <p className="mt-2 text-sm text-muted">
                  Listening: {voiceInterimTranscript}
                </p>
              )}
            </div>
          )}

          {voiceError && (
            <p className="mt-4 rounded-md border border-amber/40 bg-amber/10 p-3 text-sm text-amber">
              {voiceError}
            </p>
          )}

          <div className="mt-5 rounded-lg border border-line bg-panel p-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className={labelClass}>Voice output</p>
                <p className="mt-2 text-sm text-muted">{speechStatus}</p>
              </div>
              <button
                type="button"
                onClick={() => onTtsMutedChange(!ttsMuted)}
                disabled={!ttsSupported}
                className="shrink-0 rounded-lg border border-line bg-page/70 px-3 py-2 text-sm font-semibold text-text transition hover:border-cyan/70 hover:text-cyan disabled:cursor-not-allowed disabled:opacity-50"
              >
                {ttsMuted ? 'Unmute' : 'Mute'}
              </button>
            </div>

            <label className="mt-4 block text-xs font-bold uppercase tracking-[0.18em] text-cyan">
              Voice
              <select
                value={ttsVoiceURI}
                onChange={(event) => onTtsVoiceChange(event.target.value)}
                disabled={!ttsSupported || ttsVoices.length === 0}
                className="mt-2 w-full rounded-lg border border-line bg-page/70 px-3 py-3 text-sm normal-case tracking-normal text-text outline-none transition focus:border-cyan disabled:cursor-not-allowed disabled:opacity-50"
              >
                <option value="">System default</option>
                {ttsVoices.map((voice) => (
                  <option value={voice.voiceURI} key={voice.voiceURI}>
                    {voice.name} ({voice.lang})
                  </option>
                ))}
              </select>
            </label>

            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <button
                type="button"
                onClick={onTestSpeech}
                disabled={!ttsSupported || ttsMuted}
                className="rounded-lg border border-cyan/50 bg-cyan/10 px-4 py-3 text-sm font-semibold text-cyan transition hover:bg-cyan/15 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Test voice
              </button>
              <button
                type="button"
                onClick={onStopSpeech}
                disabled={!ttsSupported || !ttsSpeaking}
                className="rounded-lg border border-line bg-page/70 px-4 py-3 text-sm font-semibold text-text transition hover:border-cyan/70 hover:text-cyan disabled:cursor-not-allowed disabled:opacity-50"
              >
                Stop speech
              </button>
            </div>
          </div>

          {assistantError && (
            <p className="mt-4 rounded-md border border-amber/40 bg-amber/10 p-3 text-sm text-amber">
              {assistantError}
            </p>
          )}
        </aside>
      </div>

      <form
        onSubmit={onSubmit}
        className="mt-6 flex flex-col gap-3 md:flex-row"
      >
        <input
          type="text"
          value={draft}
          onChange={(event) => onDraftChange(event.target.value)}
          placeholder="Type a request for Mirrage"
          aria-label="Message the assistant"
          className="min-w-0 flex-1 rounded-lg border border-line bg-page/70 px-4 py-3 text-text outline-none transition placeholder:text-muted focus:border-cyan"
        />
        <button
          type="submit"
          disabled={assistantBusy}
          className="rounded-lg border border-cyan/50 bg-cyan/10 px-6 py-3 font-semibold text-cyan transition hover:bg-cyan/15 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {assistantBusy ? 'Sending...' : 'Send'}
        </button>
      </form>
    </div>
  );
}

interface MediaFocusProps {
  loginUrl: string;
  onClose: () => void;
  onRefresh: () => void;
  onSpotifyAction: (action: 'play' | 'pause' | 'next' | 'previous') => void;
  spotifyPlayback: SpotifyPlayback | null;
  spotifyState: SpotifyUiState;
  spotifyStatus: SpotifyStatus | null;
}

function MediaFocus({
  loginUrl,
  onClose,
  onRefresh,
  onSpotifyAction,
  spotifyPlayback,
  spotifyState,
  spotifyStatus,
}: MediaFocusProps) {
  const isConfigured = spotifyStatus?.configured ?? false;
  const isAuthenticated = spotifyStatus?.authenticated ?? false;
  const hasPlayback =
    isAuthenticated &&
    spotifyPlayback !== null &&
    spotifyPlayback.title !== null &&
    spotifyPlayback.status !== 'no_active_playback';
  const progressPercent =
    spotifyPlayback?.progress_ms != null &&
    spotifyPlayback.duration_ms != null &&
    spotifyPlayback.duration_ms > 0
      ? Math.min(
          100,
          Math.round(
            (spotifyPlayback.progress_ms / spotifyPlayback.duration_ms) * 100,
          ),
        )
      : 0;
  const playPauseAction = spotifyPlayback?.is_playing ? 'pause' : 'play';
  const playPauseLabel = spotifyPlayback?.is_playing ? 'Pause' : 'Play';
  const controlsDisabled = spotifyState.isLoading || !isAuthenticated;

  return (
    <div className={focusPanelClass}>
      <FocusHeader eyebrow="Media Focus" onClose={onClose} title="Spotify" />

      <div className="mt-10 grid items-center gap-8 md:grid-cols-[320px_1fr]">
        <div className="grid aspect-square place-items-center overflow-hidden rounded-xl border border-line bg-[linear-gradient(135deg,rgba(109,215,232,0.24),rgba(122,217,165,0.10),rgba(240,195,106,0.16))] shadow-mirror">
          {spotifyPlayback?.artwork_url ? (
            <img
              src={spotifyPlayback.artwork_url}
              alt={spotifyPlayback.album ?? 'Spotify album artwork'}
              className="h-full w-full object-cover"
            />
          ) : (
            <div className="px-8 text-center">
              <p className={labelClass}>Artwork</p>
              <p className="mt-3 text-sm text-muted">
                Album art appears after Spotify is connected and playback is
                active.
              </p>
            </div>
          )}
        </div>

        <div>
          <p className={labelClass}>
            {isAuthenticated ? 'Spotify connected' : 'Spotify integration'}
          </p>
          <h2 className="mt-4 text-4xl font-semibold text-text md:text-6xl">
            {hasPlayback
              ? spotifyPlayback.title
              : isConfigured
                ? 'Connect Spotify'
                : 'Setup needed'}
          </h2>
          <p className="mt-4 text-xl text-muted">
            {hasPlayback
              ? spotifyPlayback.artist
              : isConfigured
                ? 'Authorize your account to control playback.'
                : 'Add Spotify credentials to the backend environment.'}
          </p>

          {hasPlayback && (
            <div className="mt-6 max-w-xl">
              <p className={mutedClass}>{spotifyPlayback.album}</p>
              <p className="mt-2 text-sm text-muted">
                {spotifyPlayback.device_name
                  ? `${spotifyPlayback.device_name} (${spotifyPlayback.device_type ?? 'device'})`
                  : 'No active device reported'}
              </p>
              <div className="mt-5">
                <div className="h-2 overflow-hidden rounded-full bg-line">
                  <div
                    className="h-full rounded-full bg-cyan transition-all"
                    style={{ width: `${progressPercent}%` }}
                  />
                </div>
                <div className="mt-2 flex justify-between text-xs text-muted">
                  <span>{formatDuration(spotifyPlayback.progress_ms)}</span>
                  <span>{formatDuration(spotifyPlayback.duration_ms)}</span>
                </div>
              </div>
            </div>
          )}

          {!hasPlayback && (
            <p className={`mt-8 max-w-xl ${mutedClass}`}>
              {isAuthenticated
                ? (spotifyPlayback?.message ??
                  'Start Spotify on one of your devices, then refresh this view.')
                : 'Spotify OAuth runs through the backend so client secrets stay out of the browser.'}
            </p>
          )}

          <div className="mt-8 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => onSpotifyAction('previous')}
              disabled={controlsDisabled}
              className="rounded-full border border-line bg-panel-strong px-5 py-3 text-sm font-semibold text-text transition hover:border-cyan/70 hover:text-cyan disabled:cursor-not-allowed disabled:opacity-50"
            >
              Previous
            </button>
            <button
              type="button"
              onClick={() => onSpotifyAction(playPauseAction)}
              disabled={controlsDisabled}
              className="rounded-full border border-cyan/50 bg-cyan/10 px-6 py-3 text-sm font-semibold text-cyan transition hover:bg-cyan/15 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {spotifyState.isLoading ? 'Working...' : playPauseLabel}
            </button>
            <button
              type="button"
              onClick={() => onSpotifyAction('next')}
              disabled={controlsDisabled}
              className="rounded-full border border-line bg-panel-strong px-5 py-3 text-sm font-semibold text-text transition hover:border-cyan/70 hover:text-cyan disabled:cursor-not-allowed disabled:opacity-50"
            >
              Next
            </button>
            <button
              type="button"
              onClick={onRefresh}
              disabled={spotifyState.isLoading}
              className="rounded-full border border-line bg-page/70 px-5 py-3 text-sm font-semibold text-text transition hover:border-cyan/70 hover:text-cyan disabled:cursor-not-allowed disabled:opacity-50"
            >
              Refresh
            </button>
          </div>

          <div className="mt-8 rounded-lg border border-line bg-page/50 p-5">
            <p className={labelClass}>Connection</p>
            <p className="mt-2 text-sm text-muted">
              {spotifyStatus?.message ?? 'Checking Spotify connection.'}
            </p>
            <div className="mt-4 flex flex-wrap gap-3">
              {isConfigured && !isAuthenticated && (
                <a
                  href={loginUrl}
                  className="rounded-lg border border-green/50 bg-green/10 px-4 py-3 text-sm font-semibold text-green transition hover:bg-green/15"
                >
                  Connect Spotify
                </a>
              )}
              {spotifyPlayback?.spotify_url && (
                <a
                  href={spotifyPlayback.spotify_url}
                  target="_blank"
                  rel="noreferrer"
                  className="rounded-lg border border-line bg-panel-strong px-4 py-3 text-sm font-semibold text-text transition hover:border-cyan/70 hover:text-cyan"
                >
                  Open in Spotify
                </a>
              )}
            </div>
            {spotifyState.actionMessage && (
              <p className="mt-4 rounded-md border border-green/40 bg-green/10 p-3 text-sm text-green">
                {spotifyState.actionMessage}
              </p>
            )}
            {spotifyState.error && (
              <p className="mt-4 rounded-md border border-amber/40 bg-amber/10 p-3 text-sm text-amber">
                {spotifyState.error}
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

interface FocusHeaderProps {
  eyebrow: string;
  onClose: () => void;
  title: string;
}

function FocusHeader({ eyebrow, onClose, title }: FocusHeaderProps) {
  return (
    <header className="flex items-start justify-between gap-4">
      <div>
        <p className={labelClass}>{eyebrow}</p>
        <h1 className="mt-3 text-4xl font-semibold leading-tight text-text md:text-6xl">
          {title}
        </h1>
      </div>
      <button
        type="button"
        onClick={onClose}
        className="rounded-full border border-line bg-page/70 px-4 py-2 text-sm font-semibold text-muted transition hover:border-cyan/70 hover:text-cyan"
      >
        Close
      </button>
    </header>
  );
}
