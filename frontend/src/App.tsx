import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
  type ReactNode,
} from 'react';

import {
  activateSmartHomeScene,
  answerRelationship,
  archiveSharedContext,
  createHumanSession,
  createRelationship,
  createSharedContext,
  disableIdentityUser,
  endHumanSession,
  getApprovals,
  getAuditEvents,
  getCalendarLoginUrl,
  getCalendarStatus,
  getCalendarToday,
  getCalendarUpcoming,
  getDailyContext,
  getHealthStatus,
  getIdentityDevices,
  getIdentityMe,
  getIdentityUsers,
  getMyProfile,
  getPresenceEventsUrl,
  getPresenceSettings,
  getPresenceStatus,
  getProactiveSummary,
  getProfileDirectory,
  getRelationships,
  getSmartHomeEntities,
  getSmartHomeSensors,
  getSmartHomeStatus,
  getSpotifyLoginUrl,
  getSpotifyPlayback,
  getSpotifyStatus,
  getSharedContext,
  getSystemStatus,
  getVoiceStatus,
  getWakeEngineStatus,
  getWeather,
  runSmartHomeEntityAction,
  runSpotifyAction,
  revokeTrustedDevice,
  revokeContextShare,
  sendAssistantMessage,
  sendPresenceTransition,
  sendWakeWordDetection,
  setHumanSessionToken,
  shareContext,
  setTrustedDeviceToken,
  updateMyProfile,
} from './api';
import { AgentWorkspace } from './components/AgentWorkspace';
import {
  routeAssistantCommand,
  type AssistantCommandRoute,
  type AssistantUiAction,
} from './intentRouting';
import { demoModeConfig, mirrorModeConfig, wakeWordConfig } from './config';
import {
  demoCalendarStatus,
  demoCalendarToday,
  demoCalendarUpcoming,
  demoDailyContext,
  demoHealthStatus,
  demoIdentityPrincipal,
  demoIdentityUsers,
  demoPresenceSettings,
  demoPresenceSnapshot,
  demoProactiveSummary,
  demoSmartHomeEntities,
  demoSmartHomeSensors,
  demoSmartHomeStatus,
  demoSpotifyPlayback,
  demoSpotifyStatus,
  demoSystemStatus,
  demoTrustedDevices,
  demoVoiceStatus,
  demoWakeEngineStatus,
  demoWeather,
} from './demoData';
import type {
  Approval,
  AssistantReply,
  AuditEvent,
  CalendarEvent,
  CalendarSchedule,
  CalendarStatus,
  DailyContext,
  HealthStatus,
  IdentityPrincipal,
  IdentityUser,
  PersonalizationProfile,
  PersonalizationProfileUpdate,
  PresenceSettings,
  PresenceSnapshot,
  PresenceState,
  PresenceTransition,
  ProactiveSummary,
  Relationship,
  SmartHomeEntitiesResponse,
  SmartHomeEntity,
  SmartHomeStatus,
  SpotifyPlayback,
  SpotifyStatus,
  SharedContextItem,
  SystemStatus,
  TrustedDevice,
  VoiceStatus,
  WakeEngineStatus,
  WeatherInfo,
  VisibleProfile,
} from './types';

type FocusView =
  | 'home'
  | 'weather'
  | 'assistant'
  | 'media'
  | 'calendar'
  | 'context'
  | 'smart-home'
  | 'identity'
  | 'profile'
  | 'agents';

const focusViewValues: FocusView[] = [
  'home',
  'weather',
  'assistant',
  'media',
  'calendar',
  'context',
  'smart-home',
  'identity',
  'profile',
  'agents',
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

interface SmartHomeUiState {
  actionMessage: string | null;
  error: string | null;
  isLoading: boolean;
}

interface IdentityUiState {
  error: string | null;
  isLoading: boolean;
  message: string | null;
}

interface RelationshipUiState {
  error: string | null;
  isLoading: boolean;
  message: string | null;
}

type AssistantOrbState =
  | 'error'
  | 'idle'
  | 'listening'
  | 'returning'
  | 'sleeping'
  | 'speaking'
  | 'thinking'
  | 'wake';

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
  'ambient-focus-word text-left transition duration-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan';
const labelClass =
  'text-[0.72rem] font-bold uppercase tracking-[0.18em] text-cyan';
const focusPanelClass =
  'focus-panel animate-focus-in px-2 py-2 md:px-6 md:py-4';

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

function normalizeWakePhrase(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

function transcriptIncludesWakePhrase(transcript: string, wakePhrase: string) {
  const normalizedTranscript = normalizeWakePhrase(transcript);
  const normalizedWakePhrase = normalizeWakePhrase(wakePhrase);

  return Boolean(
    normalizedWakePhrase && normalizedTranscript.includes(normalizedWakePhrase),
  );
}

function mapPresenceStateToAssistantState(
  state: PresenceState | undefined,
  fallback: AssistantOrbState,
): AssistantOrbState {
  switch (state) {
    case 'sleeping':
      return 'sleeping';
    case 'wake_detected':
      return 'wake';
    case 'listening':
      return 'listening';
    case 'processing':
      return 'thinking';
    case 'speaking':
      return 'speaking';
    case 'returning_to_idle':
      return 'returning';
    case 'idle':
      return 'idle';
    default:
      return fallback;
  }
}

function getPresenceLabel(
  snapshot: PresenceSnapshot | null,
  fallback: string,
): string {
  if (!snapshot) {
    return fallback;
  }

  if (snapshot.state === 'idle' && snapshot.wake_word_enabled) {
    return `Say ${snapshot.wake_phrase}`;
  }

  return snapshot.message || formatStatus(snapshot.state);
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
  const wakeRecognitionRef = useRef<BrowserSpeechRecognition | null>(null);
  const handledWakeSequenceRef = useRef<number | null>(null);
  const inactivityDimTimerRef = useRef<number | null>(null);
  const inactivitySleepTimerRef = useRef<number | null>(null);
  const [now, setNow] = useState<Date>(() => new Date());
  const isDemoMode = demoModeConfig.enabled;
  const isMirrorMode = mirrorModeConfig.enabled;
  const [mirrorInactivityLevel, setMirrorInactivityLevel] =
    useState<MirrorInactivityLevel>('active');
  const [mirrorStartupVisible, setMirrorStartupVisible] =
    useState(isMirrorMode);
  const [burnInIndex, setBurnInIndex] = useState(0);
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [voiceStatus, setVoiceStatus] = useState<VoiceStatus | null>(null);
  const [presenceSnapshot, setPresenceSnapshot] =
    useState<PresenceSnapshot | null>(null);
  const [presenceSettings, setPresenceSettings] =
    useState<PresenceSettings | null>(null);
  const [wakeEngineStatus, setWakeEngineStatus] =
    useState<WakeEngineStatus | null>(null);
  const [presenceConnected, setPresenceConnected] = useState(false);
  const [presenceError, setPresenceError] = useState<string | null>(null);
  const [pendingWakeSequence, setPendingWakeSequence] = useState<number | null>(
    null,
  );
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
  const [smartHomeStatus, setSmartHomeStatus] =
    useState<SmartHomeStatus | null>(null);
  const [smartHomeEntities, setSmartHomeEntities] =
    useState<SmartHomeEntitiesResponse | null>(null);
  const [smartHomeSensors, setSmartHomeSensors] =
    useState<SmartHomeEntitiesResponse | null>(null);
  const [identityPrincipal, setIdentityPrincipal] =
    useState<IdentityPrincipal | null>(null);
  const [identityUsers, setIdentityUsers] = useState<IdentityUser[]>([]);
  const [trustedDevices, setTrustedDevices] = useState<TrustedDevice[]>([]);
  const [pendingApprovals, setPendingApprovals] = useState<Approval[]>([]);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [identityTokenDraft, setIdentityTokenDraft] = useState('');
  const [identitySessionVersion, setIdentitySessionVersion] = useState(0);
  const [profile, setProfile] = useState<PersonalizationProfile | null>(null);
  const [relationships, setRelationships] = useState<Relationship[]>([]);
  const [sharedContext, setSharedContext] = useState<SharedContextItem[]>([]);
  const [profileDirectory, setProfileDirectory] = useState<VisibleProfile[]>(
    [],
  );
  const [relationshipState, setRelationshipState] =
    useState<RelationshipUiState>({
      error: null,
      isLoading: false,
      message: null,
    });
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
  const [smartHomeState, setSmartHomeState] = useState<SmartHomeUiState>({
    actionMessage: null,
    error: null,
    isLoading: true,
  });
  const [identityState, setIdentityState] = useState<IdentityUiState>({
    error: null,
    isLoading: true,
    message: null,
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

  const refreshIdentity = useCallback(async () => {
    setIdentityState((current) => ({
      ...current,
      error: null,
      isLoading: true,
    }));

    if (isDemoMode) {
      setIdentityPrincipal(demoIdentityPrincipal);
      setIdentityUsers(demoIdentityUsers);
      setTrustedDevices(demoTrustedDevices);
      setPendingApprovals([]);
      setAuditEvents([]);
      setIdentityState({
        error: null,
        isLoading: false,
        message: 'Showing isolated sample identity data.',
      });
      return;
    }

    try {
      const principal = await getIdentityMe();
      setIdentityPrincipal(principal);

      if (principal.role === 'owner') {
        const [users, devices, approvals, audit] = await Promise.all([
          getIdentityUsers(),
          getIdentityDevices(),
          getApprovals(),
          getAuditEvents(),
        ]);
        setIdentityUsers(users);
        setTrustedDevices(devices);
        setPendingApprovals(approvals.items);
        setAuditEvents(audit.items);
      } else {
        setIdentityUsers([]);
        setTrustedDevices([]);
        setPendingApprovals([]);
        setAuditEvents([]);
      }

      setIdentityState({
        error: null,
        isLoading: false,
        message: null,
      });
    } catch {
      setIdentityPrincipal(null);
      setIdentityUsers([]);
      setTrustedDevices([]);
      setPendingApprovals([]);
      setAuditEvents([]);
      setIdentityState({
        error: 'Enter a trusted-device token for this browser session.',
        isLoading: false,
        message: null,
      });
    }
  }, [isDemoMode]);

  const refreshPersonalization = useCallback(async () => {
    if (!identityPrincipal) {
      setProfile(null);
      setRelationships([]);
      setSharedContext([]);
      setProfileDirectory([]);
      return;
    }

    setRelationshipState((current) => ({
      ...current,
      error: null,
      isLoading: true,
    }));

    if (isDemoMode) {
      setProfile({
        user_id: 'demo-owner',
        preferred_display_name: 'Sample Owner',
        preferred_language: 'en-GB',
        response_tone: 'neutral',
        response_length: 'concise',
        greeting_style: 'minimal',
        humour: 'off',
        proactivity: 'low',
        quiet_hours_start: '22:00',
        quiet_hours_end: '07:00',
        time_zone: 'Europe/London',
        spoken_announcements: false,
        personalized_greeting: true,
        cloud_personalization_opt_in: false,
        visibility: {},
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
      setRelationships([]);
      setSharedContext([]);
      setProfileDirectory([]);
      setRelationshipState({
        error: null,
        isLoading: false,
        message: 'Showing isolated sample preferences.',
      });
      return;
    }

    try {
      const [nextProfile, relationshipResult, contextResult, directory] =
        await Promise.all([
          getMyProfile(),
          getRelationships(),
          getSharedContext(),
          getProfileDirectory(),
        ]);
      setProfile(nextProfile);
      setRelationships(relationshipResult.items);
      setSharedContext(contextResult.items);
      setProfileDirectory(directory);
      setRelationshipState({
        error: null,
        isLoading: false,
        message: null,
      });
    } catch {
      setProfile(null);
      setRelationships([]);
      setSharedContext([]);
      setProfileDirectory([]);
      setRelationshipState({
        error: identityPrincipal.human_session_active
          ? 'Personalization data could not be loaded.'
          : 'Activate a temporary human session before opening private preferences.',
        isLoading: false,
        message: null,
      });
    }
  }, [identityPrincipal, isDemoMode]);

  const reportPresenceTransition = useCallback(
    async (transition: PresenceTransition) => {
      if (isDemoMode) {
        setPresenceSnapshot((current) => ({
          ...demoPresenceSnapshot,
          ...current,
          ...transition,
          event: transition.event ?? 'demo_presence_transition',
          message: transition.message ?? 'Demo presence transition.',
          previous_state: current?.state ?? demoPresenceSnapshot.state,
          sequence: (current?.sequence ?? demoPresenceSnapshot.sequence) + 1,
          source: transition.source ?? 'demo',
          state: transition.state,
          updated_at: new Date().toISOString(),
        }));
        setPresenceError(null);
        return;
      }

      try {
        const snapshot = await sendPresenceTransition({
          source: 'frontend',
          ...transition,
        });
        setPresenceSnapshot(snapshot);
        setPresenceError(null);
      } catch {
        setPresenceError('Presence service unavailable');
      }
    },
    [isDemoMode],
  );

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
      void reportPresenceTransition({
        state: 'sleeping',
        event: 'mirror_inactivity_sleep',
        message: 'Mirror is sleeping after inactivity.',
      });
    }, mirrorModeConfig.sleepTimeoutMs);
  }, [clearMirrorInactivityTimers, isMirrorMode, reportPresenceTransition]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setNow(new Date());
    }, 1000);

    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    void refreshIdentity();
  }, [identitySessionVersion, refreshIdentity]);

  useEffect(() => {
    if (activeView === 'profile') {
      void refreshPersonalization();
    }
  }, [activeView, identitySessionVersion, refreshPersonalization]);

  useEffect(() => {
    if (
      isMirrorMode &&
      ['identity', 'profile', 'agents'].includes(activeView)
    ) {
      setActiveView('home');
    }
  }, [activeView, isMirrorMode]);

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
      wakeRecognitionRef.current?.abort();
    };
  }, []);

  useEffect(() => {
    const SpeechRecognition = getSpeechRecognitionConstructor();
    if (
      !wakeWordConfig.browserListenerEnabled ||
      !SpeechRecognition ||
      !presenceSettings?.wake_word_enabled
    ) {
      wakeRecognitionRef.current?.abort();
      wakeRecognitionRef.current = null;
      return;
    }

    let shouldRestart = true;
    const wakePhrase = presenceSettings.wake_phrase;
    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = 'en-GB';

    recognition.onresult = (event) => {
      for (
        let index = event.resultIndex;
        index < event.results.length;
        index += 1
      ) {
        const result = event.results[index];
        const transcript = result?.[0]?.transcript.trim();

        if (!result?.isFinal || !transcript) {
          continue;
        }

        if (transcriptIncludesWakePhrase(transcript, wakePhrase)) {
          void sendWakeWordDetection(
            wakePhrase,
            'experimental_browser_listener',
          )
            .then((snapshot) => {
              setPresenceSnapshot(snapshot);
              setPendingWakeSequence(snapshot.sequence);
            })
            .catch(() => {
              setPresenceError(
                'Wake phrase was heard, but the backend rejected it.',
              );
            });
        }
      }
    };

    recognition.onerror = (event) => {
      setPresenceError(
        `Wake listener error: ${getVoiceErrorMessage(event.error)}`,
      );
    };

    recognition.onend = () => {
      wakeRecognitionRef.current = null;

      if (shouldRestart) {
        window.setTimeout(() => {
          try {
            recognition.start();
            wakeRecognitionRef.current = recognition;
          } catch {
            setPresenceError('Wake listener could not restart.');
          }
        }, 700);
      }
    };

    try {
      recognition.start();
      wakeRecognitionRef.current = recognition;
      setPresenceError(null);
    } catch {
      setPresenceError('Wake listener could not start.');
    }

    return () => {
      shouldRestart = false;
      recognition.abort();
      wakeRecognitionRef.current = null;
    };
  }, [presenceSettings?.wake_phrase, presenceSettings?.wake_word_enabled]);

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
      if (isDemoMode) {
        setHealthStatus(demoHealthStatus);
        setSystemStatus(demoSystemStatus);
        setVoiceStatus(demoVoiceStatus);
        setWeather(demoWeather);
        setBackendState({ error: null, isLoading: false });
        return;
      }

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
  }, [isDemoMode]);

  useEffect(() => {
    let isActive = true;

    async function loadPresence() {
      if (isDemoMode) {
        setPresenceSnapshot(demoPresenceSnapshot);
        setPresenceSettings(demoPresenceSettings);
        setWakeEngineStatus(demoWakeEngineStatus);
        setPresenceConnected(true);
        setPresenceError(null);
        return;
      }

      try {
        const [snapshot, settings, wakeEngine] = await Promise.all([
          getPresenceStatus(),
          getPresenceSettings(),
          getWakeEngineStatus(),
        ]);

        if (!isActive) {
          return;
        }

        setPresenceSnapshot(snapshot);
        setPresenceSettings(settings);
        setWakeEngineStatus(wakeEngine);
        setPresenceError(null);
      } catch {
        if (!isActive) {
          return;
        }

        setPresenceError('Presence service unavailable');
      }
    }

    loadPresence();

    if (isDemoMode) {
      return () => {
        isActive = false;
      };
    }

    const events = new EventSource(getPresenceEventsUrl());

    events.addEventListener('presence', (event) => {
      const snapshot = JSON.parse(
        (event as MessageEvent<string>).data,
      ) as PresenceSnapshot;

      setPresenceSnapshot(snapshot);
      setPresenceConnected(true);
      setPresenceError(null);

      if (snapshot.state === 'wake_detected') {
        setPendingWakeSequence(snapshot.sequence);
      }
    });

    events.onerror = () => {
      setPresenceConnected(false);
      setPresenceError('Presence event stream disconnected');
    };

    return () => {
      isActive = false;
      events.close();
    };
  }, [isDemoMode]);

  useEffect(() => {
    let isActive = true;

    async function loadSpotify() {
      if (isDemoMode) {
        setSpotifyStatus(demoSpotifyStatus);
        setSpotifyPlayback(demoSpotifyPlayback);
        setSpotifyState({
          actionMessage: null,
          error: null,
          isLoading: false,
        });
        return;
      }

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
  }, [identitySessionVersion, isDemoMode]);

  useEffect(() => {
    let isActive = true;

    async function loadCalendar() {
      if (isDemoMode) {
        setCalendarStatus(demoCalendarStatus);
        setCalendarToday(demoCalendarToday);
        setCalendarUpcoming(demoCalendarUpcoming);
        setCalendarState({
          error: null,
          isLoading: false,
        });
        return;
      }

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
  }, [identitySessionVersion, isDemoMode]);

  useEffect(() => {
    let isActive = true;

    async function loadContext() {
      if (isDemoMode) {
        setDailyContext(demoDailyContext);
        setContextState({
          error: null,
          isLoading: false,
        });
        return;
      }

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
  }, [identitySessionVersion, isDemoMode]);

  useEffect(() => {
    let isActive = true;

    async function loadProactiveSummary() {
      if (isDemoMode) {
        setProactiveSummary(demoProactiveSummary);
        setProactiveState({
          error: null,
          isLoading: false,
        });
        return;
      }

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
  }, [identitySessionVersion, isDemoMode]);

  useEffect(() => {
    let isActive = true;

    async function loadSmartHome() {
      if (isDemoMode) {
        setSmartHomeStatus(demoSmartHomeStatus);
        setSmartHomeEntities(demoSmartHomeEntities);
        setSmartHomeSensors(demoSmartHomeSensors);
        setSmartHomeState({
          actionMessage: null,
          error: null,
          isLoading: false,
        });
        return;
      }

      try {
        const [status, entities, sensors] = await Promise.all([
          getSmartHomeStatus(),
          getSmartHomeEntities(),
          getSmartHomeSensors(),
        ]);

        if (!isActive) {
          return;
        }

        setSmartHomeStatus(status);
        setSmartHomeEntities(entities);
        setSmartHomeSensors(sensors);
        setSmartHomeState({
          actionMessage: null,
          error: null,
          isLoading: false,
        });
      } catch {
        if (!isActive) {
          return;
        }

        setSmartHomeState({
          actionMessage: null,
          error: 'Smart home API unavailable',
          isLoading: false,
        });
      }
    }

    loadSmartHome();

    return () => {
      isActive = false;
    };
  }, [identitySessionVersion, isDemoMode]);

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

  const smartHomeSummary = useMemo(() => {
    if (smartHomeState.isLoading) {
      return 'Checking smart home';
    }

    if (smartHomeState.error || !smartHomeStatus) {
      return 'Smart home unavailable';
    }

    if (!smartHomeStatus.enabled) {
      return 'Smart home disabled';
    }

    if (!smartHomeStatus.configured) {
      return 'Home Assistant setup needed';
    }

    if (smartHomeStatus.connection_status !== 'connected') {
      return formatStatus(smartHomeStatus.connection_status);
    }

    return `${smartHomeStatus.entity_count} home item${
      smartHomeStatus.entity_count === 1 ? '' : 's'
    }`;
  }, [smartHomeState.error, smartHomeState.isLoading, smartHomeStatus]);

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

  const localAssistantState: AssistantOrbState = voiceListening
    ? 'listening'
    : assistantBusy
      ? 'thinking'
      : ttsSpeaking
        ? 'speaking'
        : assistantError || voiceError || backendState.error
          ? 'error'
          : 'idle';
  const assistantOrbState = mapPresenceStateToAssistantState(
    presenceSnapshot?.state,
    localAssistantState,
  );
  const voiceLabel = presenceSnapshot
    ? getPresenceLabel(presenceSnapshot, 'Voice ready')
    : voiceListening
      ? 'Listening now'
      : voiceSupported
        ? 'Voice ready'
        : voiceStatus?.listening
          ? 'Listening'
          : 'Voice planned';
  const presenceDetail = presenceSnapshot
    ? `${formatStatus(presenceSnapshot.state)} / ${presenceConnected ? 'event stream online' : 'snapshot only'}`
    : (presenceError ?? 'Presence service connecting');
  const systemLabel = backendState.error
    ? 'System offline'
    : formatStatus(systemStatus?.status);
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
      {
        label: 'Home',
        status: smartHomeSummary,
        tone: smartHomeState.isLoading
          ? 'checking'
          : smartHomeStatus?.connection_status === 'connected'
            ? 'online'
            : 'planned',
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
      smartHomeState.isLoading,
      smartHomeStatus,
      smartHomeSummary,
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
    void reportPresenceTransition({
      state: 'processing',
      event: 'intent_processing_started',
      transcript: message,
      message: 'Processing local intent command.',
    });

    if (command.intent === 'daily_context') {
      setAssistantBusy(true);

      try {
        const [context, result] = isDemoMode
          ? await Promise.resolve([
              demoDailyContext,
              {
                context_action: 'daily',
                model: null,
                provider: 'demo',
                reply:
                  'Daily briefing: weather is calm, calendar has two focused blocks, and the best next step is finishing Mirrage v1 polish.',
              } satisfies AssistantReply,
            ])
          : await Promise.all([
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
        void reportPresenceTransition({
          state: 'speaking',
          event: 'assistant_response_ready',
          transcript: message,
          assistant_reply: result.reply,
          message: 'Assistant response is ready to speak.',
        });
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
        const [status, today, upcoming] = isDemoMode
          ? await Promise.resolve([
              demoCalendarStatus,
              demoCalendarToday,
              demoCalendarUpcoming,
            ])
          : await Promise.all([
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
        void reportPresenceTransition({
          state: 'speaking',
          event: 'assistant_response_ready',
          transcript: message,
          assistant_reply: response,
          message: 'Assistant response is ready to speak.',
        });
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
    void reportPresenceTransition({
      state: 'speaking',
      event: 'assistant_response_ready',
      transcript: message,
      assistant_reply: command.response,
      message: 'Assistant response is ready to speak.',
    });
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

    if (isDemoMode) {
      const demoReply =
        'Demo response: Mirrage is ready to route this through the backend assistant runtime when demo mode is off.';

      setAssistantProvider('demo');
      setAssistantMessages((messages) => [
        ...messages,
        {
          role: 'assistant',
          text: demoReply,
          meta: 'Demo provider',
        },
      ]);
      speakText(demoReply);
      setDraft('');
      setAssistantBusy(false);
      return;
    }

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
    settlePresenceAfterSpeech();
  }

  function settlePresenceAfterSpeech() {
    void reportPresenceTransition({
      state: 'returning_to_idle',
      event: 'speech_synthesis_finished',
      message: 'Conversation is ending.',
    });

    window.setTimeout(() => {
      void reportPresenceTransition({
        state: 'idle',
        event: 'conversation_idle',
        message: 'Assistant presence is idle.',
      });
    }, 900);
  }

  function speakText(text: string): boolean {
    if (!ttsSupportedRef.current || ttsMutedRef.current || !text.trim()) {
      settlePresenceAfterSpeech();
      return false;
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
        void reportPresenceTransition({
          state: 'speaking',
          event: 'speech_synthesis_started',
          assistant_reply: text,
          message: 'Assistant response is being spoken.',
        });
      }
    };

    utterance.onend = () => {
      if (speechRequestRef.current === requestId) {
        setTtsSpeaking(false);
        settlePresenceAfterSpeech();
      }
    };

    utterance.onerror = () => {
      if (speechRequestRef.current === requestId) {
        setTtsSpeaking(false);
        settlePresenceAfterSpeech();
      }
    };

    synthesis.speak(utterance);
    return true;
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
        void reportPresenceTransition({
          state: 'returning_to_idle',
          event: 'speech_recognition_error',
          message: getVoiceErrorMessage(event.error),
        });
      };

      recognition.onend = () => {
        setVoiceListening(false);
        recognitionRef.current = null;
        setVoiceInterimTranscript('');

        if (capturedTranscript) {
          void reportPresenceTransition({
            state: 'processing',
            event: 'speech_recognition_finished',
            transcript: capturedTranscript,
            message: 'Speech transcript captured.',
          });
          void sendAssistantRequest(capturedTranscript, 'voice');
          return;
        }

        setVoiceError((currentError) => currentError ?? 'No speech was heard.');
        void reportPresenceTransition({
          state: 'returning_to_idle',
          event: 'speech_recognition_empty',
          message: 'No speech was heard.',
        });
      };

      recognitionRef.current = recognition;
      setVoiceListening(true);
      void reportPresenceTransition({
        state: 'listening',
        event: 'speech_recognition_started',
        message: 'Listening for the user request.',
      });
      recognition.start();
    } catch (error) {
      setVoiceListening(false);
      recognitionRef.current = null;
      const message =
        error instanceof Error
          ? error.message
          : 'Microphone access could not be started.';
      setVoiceError(message);
      void reportPresenceTransition({
        state: 'returning_to_idle',
        event: 'microphone_start_failed',
        message,
      });
    }
  }

  function stopVoiceCapture() {
    registerMirrorActivity();
    recognitionRef.current?.stop();
  }

  useEffect(() => {
    if (
      pendingWakeSequence === null ||
      handledWakeSequenceRef.current === pendingWakeSequence ||
      !voiceSupported ||
      assistantBusy ||
      voiceListening
    ) {
      return;
    }

    handledWakeSequenceRef.current = pendingWakeSequence;
    setActiveView('assistant');
    registerMirrorActivity();
    void startVoiceCapture();
    // startVoiceCapture intentionally stays outside this dependency list so a
    // wake event is handled once per backend sequence, not once per render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assistantBusy, pendingWakeSequence, voiceListening, voiceSupported]);

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

    if (isDemoMode) {
      setSpotifyStatus(demoSpotifyStatus);
      setSpotifyPlayback(demoSpotifyPlayback);
      setSpotifyState({
        actionMessage: 'Demo playback refreshed.',
        error: null,
        isLoading: false,
      });
      return;
    }

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

    if (isDemoMode) {
      setCalendarStatus(demoCalendarStatus);
      setCalendarToday(demoCalendarToday);
      setCalendarUpcoming(demoCalendarUpcoming);
      setCalendarState({
        error: null,
        isLoading: false,
      });
      return;
    }

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

    if (isDemoMode) {
      setDailyContext(demoDailyContext);
      setContextState({
        error: null,
        isLoading: false,
      });
      return demoDailyContext;
    }

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

  async function refreshSmartHome() {
    registerMirrorActivity();

    if (isDemoMode) {
      setSmartHomeStatus(demoSmartHomeStatus);
      setSmartHomeEntities(demoSmartHomeEntities);
      setSmartHomeSensors(demoSmartHomeSensors);
      setSmartHomeState({
        actionMessage: 'Demo smart home state refreshed.',
        error: null,
        isLoading: false,
      });
      return;
    }

    setSmartHomeState((current) => ({
      ...current,
      error: null,
      isLoading: true,
    }));

    try {
      const [status, entities, sensors] = await Promise.all([
        getSmartHomeStatus(),
        getSmartHomeEntities(),
        getSmartHomeSensors(),
      ]);

      setSmartHomeStatus(status);
      setSmartHomeEntities(entities);
      setSmartHomeSensors(sensors);
      setSmartHomeState((current) => ({
        ...current,
        error: null,
        isLoading: false,
      }));
    } catch {
      setSmartHomeState((current) => ({
        ...current,
        error: 'Smart home API unavailable',
        isLoading: false,
      }));
    }
  }

  async function handleSmartHomeEntityAction(
    entity: SmartHomeEntity,
    action: 'turn-on' | 'turn-off',
  ) {
    registerMirrorActivity();

    if (isDemoMode) {
      setSmartHomeState({
        actionMessage: `Demo ${entity.name} ${action === 'turn-on' ? 'turned on' : 'turned off'}.`,
        error: null,
        isLoading: false,
      });
      return;
    }

    setSmartHomeState({
      actionMessage: null,
      error: null,
      isLoading: true,
    });

    try {
      const result = await runSmartHomeEntityAction(entity.entity_id, action);
      await refreshSmartHome();
      setSmartHomeState((current) => ({
        ...current,
        actionMessage: result.message,
        error: null,
        isLoading: false,
      }));
    } catch {
      setSmartHomeState({
        actionMessage: null,
        error: `${entity.name} could not be changed. Check Home Assistant and Mirrage safety rules.`,
        isLoading: false,
      });
    }
  }

  async function handleSmartHomeSceneActivate(entity: SmartHomeEntity) {
    registerMirrorActivity();

    if (isDemoMode) {
      setSmartHomeState({
        actionMessage: `Demo scene ${entity.name} activated.`,
        error: null,
        isLoading: false,
      });
      return;
    }

    setSmartHomeState({
      actionMessage: null,
      error: null,
      isLoading: true,
    });

    try {
      const result = await activateSmartHomeScene(entity.entity_id);
      await refreshSmartHome();
      setSmartHomeState((current) => ({
        ...current,
        actionMessage: result.message,
        error: null,
        isLoading: false,
      }));
    } catch {
      setSmartHomeState({
        actionMessage: null,
        error: `${entity.name} could not be activated. Check Home Assistant and Mirrage safety rules.`,
        isLoading: false,
      });
    }
  }

  async function handleSpotifyAction(
    action: 'play' | 'pause' | 'next' | 'previous',
  ) {
    registerMirrorActivity();

    if (isDemoMode) {
      setSpotifyState({
        actionMessage: `Demo Spotify ${action} action handled.`,
        error: null,
        isLoading: false,
      });
      return;
    }

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

  function handleIdentityTokenSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!identityTokenDraft.trim() || isDemoMode) {
      return;
    }
    setTrustedDeviceToken(identityTokenDraft);
    setIdentityTokenDraft('');
    setIdentitySessionVersion((current) => current + 1);
    setIdentityState({
      error: null,
      isLoading: true,
      message: 'Authenticating this browser session.',
    });
  }

  function handleIdentityDisconnect() {
    setHumanSessionToken(null);
    setTrustedDeviceToken(null);
    setIdentityPrincipal(null);
    setIdentitySessionVersion((current) => current + 1);
  }

  async function handleActivateHumanSession() {
    if (isDemoMode) {
      return;
    }
    setIdentityState({ error: null, isLoading: true, message: null });
    try {
      const enrollment = await createHumanSession();
      setHumanSessionToken(enrollment.token);
      setIdentitySessionVersion((current) => current + 1);
      setIdentityState({
        error: null,
        isLoading: false,
        message: 'Temporary human session activated for this device.',
      });
    } catch {
      setIdentityState({
        error: 'The temporary human session could not be activated.',
        isLoading: false,
        message: null,
      });
    }
  }

  async function handleEndHumanSession() {
    if (isDemoMode) {
      return;
    }
    setIdentityState({ error: null, isLoading: true, message: null });
    try {
      await endHumanSession();
    } catch {
      // Clear the local token even if the backend session already expired.
    }
    setHumanSessionToken(null);
    setIdentitySessionVersion((current) => current + 1);
    setIdentityState({
      error: null,
      isLoading: false,
      message: 'Temporary human session ended.',
    });
  }

  async function handleProfileUpdate(update: PersonalizationProfileUpdate) {
    if (isDemoMode) {
      setProfile((current) => (current ? { ...current, ...update } : current));
      setRelationshipState({
        error: null,
        isLoading: false,
        message: 'Demo preferences updated locally.',
      });
      return;
    }
    setRelationshipState({ error: null, isLoading: true, message: null });
    try {
      const result = await updateMyProfile(update);
      setProfile(result);
      setRelationshipState({
        error: null,
        isLoading: false,
        message: 'Communication preferences saved.',
      });
    } catch {
      setRelationshipState({
        error: 'Communication preferences could not be saved.',
        isLoading: false,
        message: null,
      });
    }
  }

  async function handleRelationshipCreate(
    targetUserId: string,
    relationshipType: string,
  ) {
    if (isDemoMode) {
      return;
    }
    setRelationshipState({ error: null, isLoading: true, message: null });
    try {
      await createRelationship(targetUserId, relationshipType);
      await refreshPersonalization();
      setRelationshipState({
        error: null,
        isLoading: false,
        message: 'Relationship request sent for confirmation.',
      });
    } catch {
      setRelationshipState({
        error: 'The relationship request could not be created.',
        isLoading: false,
        message: null,
      });
    }
  }

  async function handleRelationshipAction(
    relationship: Relationship,
    action: 'accept' | 'reject' | 'archive',
  ) {
    if (isDemoMode) {
      return;
    }
    setRelationshipState({ error: null, isLoading: true, message: null });
    try {
      await answerRelationship(relationship.public_id, action);
      await refreshPersonalization();
      setRelationshipState({
        error: null,
        isLoading: false,
        message: `Relationship ${action} completed.`,
      });
    } catch {
      setRelationshipState({
        error: `The relationship could not be ${action}ed.`,
        isLoading: false,
        message: null,
      });
    }
  }

  async function handleSharedContextCreate(input: {
    context_type: SharedContextItem['context_type'];
    title: string;
    value: string;
    visibility: SharedContextItem['visibility'];
  }) {
    if (isDemoMode) {
      return;
    }
    setRelationshipState({ error: null, isLoading: true, message: null });
    try {
      await createSharedContext(input);
      await refreshPersonalization();
      setRelationshipState({
        error: null,
        isLoading: false,
        message:
          'Shared context created. It remains private unless you share it.',
      });
    } catch {
      setRelationshipState({
        error: 'Shared context could not be created.',
        isLoading: false,
        message: null,
      });
    }
  }

  async function handleSharedContextAccess(
    item: SharedContextItem,
    action: 'archive' | 'share' | 'revoke',
    userId?: string,
  ) {
    if (isDemoMode) {
      return;
    }
    setRelationshipState({ error: null, isLoading: true, message: null });
    try {
      if (action === 'archive') {
        await archiveSharedContext(item.public_id);
      } else if (action === 'share' && userId) {
        await shareContext(item.public_id, userId);
      } else if (action === 'revoke' && userId) {
        await revokeContextShare(item.public_id, userId);
      }
      await refreshPersonalization();
      setRelationshipState({
        error: null,
        isLoading: false,
        message: `Shared context ${action} completed.`,
      });
    } catch {
      setRelationshipState({
        error: `Shared context ${action} failed.`,
        isLoading: false,
        message: null,
      });
    }
  }

  async function handleDisableIdentityUser(user: IdentityUser) {
    if (isDemoMode || user.role === 'owner') {
      return;
    }
    setIdentityState({ error: null, isLoading: true, message: null });
    try {
      await disableIdentityUser(user.public_id);
      await refreshIdentity();
      setIdentityState({
        error: null,
        isLoading: false,
        message: `${user.display_name} was disabled.`,
      });
    } catch {
      setIdentityState({
        error: 'The user could not be disabled.',
        isLoading: false,
        message: null,
      });
    }
  }

  async function handleRevokeTrustedDevice(device: TrustedDevice) {
    if (isDemoMode || device.public_id === identityPrincipal?.device_id) {
      return;
    }
    setIdentityState({ error: null, isLoading: true, message: null });
    try {
      await revokeTrustedDevice(device.public_id);
      await refreshIdentity();
      setIdentityState({
        error: null,
        isLoading: false,
        message: `${device.display_name} was revoked.`,
      });
    } catch {
      setIdentityState({
        error: 'The trusted device could not be revoked.',
        isLoading: false,
        message: null,
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
      <div className="ambient-glass-layer" />

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
            burnInOffset={burnInOffset}
            currentDate={currentDate}
            currentTime={currentTime}
            inactivityLevel={mirrorInactivityLevel}
            identityName={
              identityPrincipal?.human_session_active
                ? identityPrincipal.display_name
                : null
            }
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
            identityName={identityPrincipal?.display_name ?? null}
            assistantOrbState={assistantOrbState}
            onOpen={openFocus}
            presenceDetail={presenceDetail}
            smartHomeSummary={smartHomeSummary}
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
            presenceDetail={presenceDetail}
            presenceError={presenceError}
            presenceSettings={presenceSettings}
            wakeEngineStatus={wakeEngineStatus}
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

        {activeView === 'smart-home' && (
          <SmartHomeFocus
            entities={smartHomeEntities}
            onClose={closeFocus}
            onEntityAction={(entity, action) =>
              void handleSmartHomeEntityAction(entity, action)
            }
            onRefresh={() => void refreshSmartHome()}
            onSceneActivate={(entity) =>
              void handleSmartHomeSceneActivate(entity)
            }
            sensors={smartHomeSensors}
            smartHomeState={smartHomeState}
            status={smartHomeStatus}
          />
        )}

        {activeView === 'identity' && !isMirrorMode && (
          <IdentityFocus
            auditEvents={auditEvents}
            devices={trustedDevices}
            identityState={identityState}
            onClose={closeFocus}
            onActivateHumanSession={() => void handleActivateHumanSession()}
            onDisableUser={(user) => void handleDisableIdentityUser(user)}
            onDisconnect={handleIdentityDisconnect}
            onEndHumanSession={() => void handleEndHumanSession()}
            onRefresh={() => void refreshIdentity()}
            onRevokeDevice={(device) => void handleRevokeTrustedDevice(device)}
            onTokenChange={setIdentityTokenDraft}
            onTokenSubmit={handleIdentityTokenSubmit}
            pendingApprovals={pendingApprovals}
            principal={identityPrincipal}
            tokenDraft={identityTokenDraft}
            users={identityUsers}
          />
        )}

        {activeView === 'profile' && !isMirrorMode && (
          <RelationshipFocus
            directory={profileDirectory}
            onClose={closeFocus}
            onCreateRelationship={(target, type) =>
              void handleRelationshipCreate(target, type)
            }
            onCreateSharedContext={(input) =>
              void handleSharedContextCreate(input)
            }
            onProfileUpdate={(update) => void handleProfileUpdate(update)}
            onRefresh={() => void refreshPersonalization()}
            onRelationshipAction={(relationship, action) =>
              void handleRelationshipAction(relationship, action)
            }
            onSharedContextAction={(item, action, userId) =>
              void handleSharedContextAccess(item, action, userId)
            }
            principal={identityPrincipal}
            profile={profile}
            relationships={relationships}
            sharedContext={sharedContext}
            state={relationshipState}
            users={identityUsers}
          />
        )}

        {activeView === 'agents' && !isMirrorMode && (
          <AgentWorkspace onClose={closeFocus} />
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
  assistantOrbState: AssistantOrbState;
  backendLabel: string;
  calendarSummary: string;
  contextSummary: string;
  currentDate: string;
  currentTime: string;
  identityName: string | null;
  onOpen: (view: Exclude<FocusView, 'home'>) => void;
  presenceDetail: string;
  smartHomeSummary: string;
  systemLabel: string;
  voiceLabel: string;
  weather: WeatherInfo | null;
  weatherSummary: string;
}

function HomeState({
  assistantOrbState,
  backendLabel,
  calendarSummary,
  contextSummary,
  currentDate,
  currentTime,
  identityName,
  onOpen,
  presenceDetail,
  smartHomeSummary,
  systemLabel,
  voiceLabel,
  weather,
  weatherSummary,
}: HomeStateProps) {
  return (
    <div className="ambient-home min-h-[82vh]">
      <header className="ambient-home-clock">
        <div>
          <p className={labelClass}>Mirrage</p>
          <h1 className="mt-4 text-[4.5rem] font-semibold leading-none tracking-normal text-text sm:text-[7rem] md:text-[11rem]">
            {currentTime}
          </h1>
          <p className="mt-4 text-lg text-muted">{currentDate}</p>
        </div>
      </header>

      <section className="ambient-home-weather" aria-label="Weather">
        <button
          type="button"
          className="text-left"
          onClick={() => onOpen('weather')}
        >
          <span className={labelClass}>Weather</span>
          <strong>{formatTemperature(weather)}</strong>
          <span>{weatherSummary}</span>
        </button>
      </section>

      <section className="ambient-presence" aria-label="Assistant status">
        <button
          type="button"
          onClick={() => onOpen('assistant')}
          className={`ambient-presence-button ambient-presence-${assistantOrbState}`}
        >
          <span>Mirrage</span>
          <strong>{voiceLabel}</strong>
        </button>
        <div className="presence-wave" aria-hidden="true" />
      </section>

      <nav className="ambient-word-nav" aria-label="Ambient focus controls">
        <button
          type="button"
          className={focusButtonBase}
          onClick={() => onOpen('weather')}
        >
          Weather
        </button>

        <button
          type="button"
          className={focusButtonBase}
          onClick={() => onOpen('assistant')}
        >
          Assistant
        </button>

        <button
          type="button"
          className={focusButtonBase}
          onClick={() => onOpen('media')}
        >
          Media
        </button>

        <button
          type="button"
          className={focusButtonBase}
          onClick={() => onOpen('calendar')}
        >
          Calendar
        </button>

        <button
          type="button"
          className={focusButtonBase}
          onClick={() => onOpen('context')}
        >
          Context
        </button>

        <button
          type="button"
          className={focusButtonBase}
          onClick={() => onOpen('smart-home')}
        >
          Home
        </button>

        <button
          type="button"
          className={focusButtonBase}
          onClick={() => onOpen('identity')}
        >
          Identity
        </button>

        <button
          type="button"
          className={focusButtonBase}
          onClick={() => onOpen('profile')}
        >
          Profile
        </button>

        <button
          type="button"
          className={focusButtonBase}
          onClick={() => onOpen('agents')}
        >
          Agents
        </button>
      </nav>

      <footer className="ambient-home-status">
        <p>
          {identityName ? `Signed in as ${identityName}` : 'Anonymous session'}
        </p>
        <p>{backendLabel}</p>
        <p>{voiceLabel}</p>
        <p>{presenceDetail}</p>
        <p>{calendarSummary}</p>
        <p>{contextSummary}</p>
        <p>{smartHomeSummary}</p>
        <p>{systemLabel}</p>
      </footer>
    </div>
  );
}

interface MirrorHomeStateProps {
  assistantOrbState: AssistantOrbState;
  burnInOffset: BurnInOffset;
  currentDate: string;
  currentTime: string;
  inactivityLevel: MirrorInactivityLevel;
  identityName: string | null;
  onOpen: (view: Exclude<FocusView, 'home'>) => void;
  proactiveNudge: string;
  proactiveSummary: ProactiveSummary | null;
  voiceLabel: string;
  weather: WeatherInfo | null;
  weatherSummary: string;
}

function MirrorHomeState({
  assistantOrbState,
  burnInOffset,
  currentDate,
  currentTime,
  inactivityLevel,
  identityName,
  onOpen,
  proactiveNudge,
  proactiveSummary,
  voiceLabel,
  weather,
  weatherSummary,
}: MirrorHomeStateProps) {
  const transform = `translate(${burnInOffset.x}px, ${burnInOffset.y}px)`;
  const assistantStatus =
    assistantOrbState === 'idle'
      ? voiceLabel
      : `Mirrage ${formatStatus(assistantOrbState)}`;

  return (
    <div
      className={`mirror-home ${inactivityLevel === 'sleep' ? 'mirror-home-sleep' : ''}`}
    >
      <div className="mirror-clock mirror-burn" style={{ transform }}>
        <p className={labelClass}>
          {identityName ? `Mirrage / ${identityName}` : 'Mirrage'}
        </p>
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

      <div className="mirror-presence-zone mirror-burn">
        <button
          type="button"
          className={`mirror-presence-button mirror-presence-${assistantOrbState}`}
          onClick={() => onOpen('assistant')}
          aria-label="Open assistant focus"
        >
          <span>Mirrage</span>
          <strong>{assistantStatus}</strong>
        </button>
        <div className="presence-wave" aria-hidden="true" />
      </div>

      <nav className="mirror-focus-rail" aria-label="Mirror focus views">
        <button type="button" onClick={() => onOpen('assistant')}>
          Assistant
        </button>
        <button type="button" onClick={() => onOpen('weather')}>
          Weather
        </button>
        <button type="button" onClick={() => onOpen('context')}>
          Context
        </button>
        <button type="button" onClick={() => onOpen('calendar')}>
          Calendar
        </button>
        <button type="button" onClick={() => onOpen('media')}>
          Media
        </button>
        <button type="button" onClick={() => onOpen('smart-home')}>
          Home
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
        eyebrow="Weather"
        onClose={onClose}
        title={weatherOnline ? weather.location : 'Weather unavailable'}
      />

      <div className="ambient-weather-scene">
        <p className="ambient-temperature">{formatTemperature(weather)}</p>
        <p className="ambient-condition">
          {weatherOnline
            ? weather.condition
            : 'Weather data is not available right now.'}
        </p>
        <div className="ambient-detail-line">
          <span>Open-Meteo via backend</span>
          <span>{formatUpdated(weather?.updated)}</span>
          <span>
            {weatherOnline ? 'Forecast source online' : 'Fallback state active'}
          </span>
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
  const firstSuggestion = suggestions[0];
  const memorySummary =
    goals[0]?.value ??
    routines[0]?.value ??
    preferences[0]?.value ??
    'Nothing important to remember.';

  return (
    <div className={focusPanelClass}>
      <FocusHeader
        eyebrow="Daily Briefing"
        onClose={onClose}
        title={context ? 'Daily briefing' : 'Context unavailable'}
      />

      <div className="ambient-quiet-actions">
        <button
          type="button"
          onClick={onRefresh}
          disabled={contextState.isLoading}
          className="ambient-text-button"
        >
          {contextState.isLoading ? 'Refreshing...' : 'Refresh'}
        </button>
        <p>
          {context?.message ??
            'Context loads from backend weather, calendar, and local memory.'}
        </p>
      </div>

      {contextState.error && (
        <p className="ambient-warning">{contextState.error}</p>
      )}

      <section className="ambient-briefing">
        <div className="ambient-briefing-lead">
          <span>{context?.date ?? 'No daily context yet'}</span>
          <p>
            {proactiveSummary?.message ??
              context?.message ??
              'Start the backend and refresh this view.'}
          </p>
        </div>

        <dl className="ambient-briefing-list">
          <div>
            <dt>Weather</dt>
            <dd>{context?.weather.summary ?? 'Weather is not loaded.'}</dd>
          </div>
          <div>
            <dt>Schedule</dt>
            <dd>{context?.calendar.message ?? 'Calendar is not loaded.'}</dd>
          </div>
          <div>
            <dt>Suggested Focus</dt>
            <dd>
              {firstSuggestion
                ? `${firstSuggestion.title}. ${firstSuggestion.reason}`
                : 'No focus suggestion yet.'}
            </dd>
          </div>
          <div>
            <dt>Memory</dt>
            <dd>{memorySummary}</dd>
          </div>
        </dl>

        {todayEvents.length > 0 && (
          <div className="ambient-briefing-events">
            <p className={labelClass}>Today</p>
            <CalendarEventList events={todayEvents.slice(0, 4)} mode="today" />
          </div>
        )}

        {(goals.length > 0 ||
          routines.length > 0 ||
          preferences.length > 0) && (
          <div className="ambient-memory-stream">
            <MemoryLineList
              emptyText="Nothing important to remember."
              items={[...goals, ...routines, ...preferences].slice(0, 5)}
            />
          </div>
        )}
      </section>
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
    <div className="ambient-line-list">
      {items.map((item) => (
        <div className="ambient-line-item" key={item.id}>
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
    ? 'Today'
    : isConfigured
      ? 'Connect Calendar'
      : 'Calendar setup';

  return (
    <div className={focusPanelClass}>
      <FocusHeader eyebrow="Calendar" onClose={onClose} title={title} />

      <div className="ambient-quiet-actions">
        <button
          type="button"
          onClick={onRefresh}
          disabled={calendarState.isLoading}
          className="ambient-text-button"
        >
          {calendarState.isLoading ? 'Refreshing' : 'Refresh'}
        </button>
        <p>{calendarStatus?.message ?? 'Checking Google Calendar.'}</p>
      </div>

      {calendarState.error && (
        <p className="ambient-warning">{calendarState.error}</p>
      )}

      {!isAuthenticated ? (
        <section className="ambient-onboarding">
          <p className={labelClass}>Calendar</p>
          <h2>
            {isConfigured
              ? 'Bring today into the glass.'
              : 'Add Calendar credentials to begin.'}
          </h2>
          <p>
            {isConfigured
              ? 'Connect Google Calendar and Mirrage will show your day as a quiet timeline, not a settings panel.'
              : 'The backend is ready for a read-only Google Calendar connection when credentials are available.'}
          </p>
          {isConfigured && (
            <a href={loginUrl} className="ambient-text-button">
              Connect Google Calendar
            </a>
          )}
        </section>
      ) : (
        <section className="ambient-calendar-scene">
          <div className="ambient-calendar-summary">
            <span>{today?.date ?? 'Schedule not loaded'}</span>
            <p>
              {todayEvents.length > 0
                ? `${todayEvents.length} event${todayEvents.length === 1 ? '' : 's'} today`
                : 'No events today'}
            </p>
          </div>

          {todayEvents.length > 0 ? (
            <CalendarEventList events={todayEvents} mode="today" />
          ) : (
            <p className="ambient-empty-line">Your daily schedule is clear.</p>
          )}

          <div className="ambient-upcoming">
            <p className={labelClass}>Upcoming</p>
            <p>{upcoming?.message ?? 'Next events appear after connection.'}</p>
            {upcomingEvents.length > 0 && (
              <CalendarEventList
                events={upcomingEvents.slice(0, 5)}
                mode="upcoming"
              />
            )}
          </div>
        </section>
      )}
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
    <div className="ambient-timeline">
      {events.map((event) => (
        <article className="ambient-event" key={`${event.id}-${event.start}`}>
          <time>
            {mode === 'today'
              ? formatCalendarEventTime(event)
              : formatCalendarEventDateTime(event)}
          </time>
          <div>
            <h2>{event.title}</h2>
            {event.location && <p>{event.location}</p>}
          </div>

          {event.html_link && (
            <a href={event.html_link} target="_blank" rel="noreferrer">
              Open
            </a>
          )}
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
  presenceDetail: string;
  presenceError: string | null;
  presenceSettings: PresenceSettings | null;
  wakeEngineStatus: WakeEngineStatus | null;
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
  presenceDetail,
  presenceError,
  presenceSettings,
  wakeEngineStatus,
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
  const stateCopy: Record<AssistantOrbState, string> = {
    error: 'Something needs attention.',
    idle: 'Ready when you are.',
    listening: 'Listening for your request.',
    returning: 'Settling back into the mirror.',
    sleeping: 'Mirror is resting.',
    speaking: 'Speaking the response.',
    thinking: 'Composing a response.',
    wake: 'Wake phrase detected.',
  };
  const transcriptText =
    voiceTranscript ||
    voiceInterimTranscript ||
    latestUserMessage?.text ||
    'Say something when you are ready.';
  const replyText = latestAssistantMessage?.text ?? 'Standing by.';
  const transcriptLabel = voiceListening
    ? 'Listening'
    : assistantBusy
      ? 'Processing'
      : ttsSpeaking
        ? 'Speaking'
        : 'Transcript';

  return (
    <div
      className={`${focusPanelClass} ambient-assistant-focus ${
        isMirrorMode ? 'ambient-assistant-mirror' : ''
      }`}
    >
      <FocusHeader eyebrow="Assistant" onClose={onClose} title="Conversation" />

      <section className="ambient-conversation">
        <button
          type="button"
          className={`ambient-presence-button ambient-presence-${assistantOrbState}`}
          onClick={voiceListening ? onStopVoice : onStartVoice}
          disabled={!voiceSupported || assistantBusy}
          aria-label={voiceButtonLabel}
        >
          <span>Mirrage</span>
          <strong>{formatStatus(assistantOrbState)}</strong>
        </button>
        <div
          className={`assistant-presence-field assistant-presence-${assistantOrbState}`}
          aria-hidden="true"
        >
          <span />
          <span />
          <span />
          <span />
          <span />
          <span />
          <span />
        </div>
        <p className="assistant-state-copy">{stateCopy[assistantOrbState]}</p>

        <div className="ambient-transcript">
          <p className={labelClass}>{transcriptLabel}</p>
          <p>{transcriptText}</p>
        </div>

        <div className="ambient-reply">
          <p className={labelClass}>Mirrage</p>
          <p>{replyText}</p>
          {latestAssistantMessage?.meta && (
            <span>{latestAssistantMessage.meta}</span>
          )}
        </div>
      </section>

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
        <button
          type="button"
          onClick={onTestSpeech}
          disabled={!ttsSupported || ttsMuted}
        >
          Test voice
        </button>
      </div>

      <label className="ambient-voice-select">
        Voice
        <select
          value={ttsVoiceURI}
          onChange={(event) => onTtsVoiceChange(event.target.value)}
          disabled={!ttsSupported || ttsVoices.length === 0}
        >
          <option value="">System default</option>
          {ttsVoices.map((voice) => (
            <option value={voice.voiceURI} key={voice.voiceURI}>
              {voice.name} ({voice.lang})
            </option>
          ))}
        </select>
      </label>

      {!isMirrorMode && (
        <section
          className="ambient-presence-settings"
          aria-label="Presence settings"
        >
          <p className={labelClass}>Presence</p>
          <p>{presenceDetail}</p>
          <p>
            Wake phrase:{' '}
            <strong>{presenceSettings?.wake_phrase ?? 'Hey Mirrage'}</strong>
          </p>
          <p>
            Engine:{' '}
            <strong>{presenceSettings?.wake_word_engine ?? 'adapter'}</strong>
            {wakeWordConfig.browserListenerEnabled
              ? ' with experimental browser listener enabled'
              : ' with local adapter expected'}
          </p>
          <p>
            Local wake engine:{' '}
            <strong>
              {wakeEngineStatus
                ? `${formatStatus(wakeEngineStatus.status)} / ${wakeEngineStatus.provider}`
                : 'Checking'}
            </strong>
          </p>
          <p>
            Wake model:{' '}
            <strong>
              {wakeEngineStatus?.model_configured
                ? 'Configured'
                : 'Not configured'}
            </strong>
          </p>
        </section>
      )}

      <p className="ambient-assistant-status">
        {presenceError ??
          voiceError ??
          assistantError ??
          (voiceSupported
            ? microphoneReady
              ? `${speechStatus} Provider: ${assistantProvider ?? 'waiting'}.`
              : 'Microphone permission is requested on first use.'
            : 'Speech recognition is not supported in this browser.')}
      </p>
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
      <FocusHeader eyebrow="Media" onClose={onClose} title="Now playing" />

      <div
        className={`ambient-media-scene ${spotifyPlayback?.artwork_url ? '' : 'ambient-media-scene-empty'}`}
      >
        {spotifyPlayback?.artwork_url && (
          <div className="ambient-artwork">
            <img
              src={spotifyPlayback.artwork_url}
              alt={spotifyPlayback.album ?? 'Spotify album artwork'}
              className="h-full w-full object-cover"
            />
          </div>
        )}

        <div className="ambient-media-copy">
          <p className={labelClass}>
            {isAuthenticated ? 'Spotify connected' : 'Spotify integration'}
          </p>
          <h2>
            {hasPlayback
              ? spotifyPlayback.title
              : isConfigured
                ? 'Connect Spotify'
                : 'Setup needed'}
          </h2>
          <p>
            {hasPlayback
              ? spotifyPlayback.artist
              : isConfigured
                ? 'Authorize your account to control playback.'
                : 'Add Spotify credentials to the backend environment.'}
          </p>

          {hasPlayback && (
            <div className="ambient-playback">
              <p>{spotifyPlayback.album}</p>
              <p>
                {spotifyPlayback.device_name
                  ? `${spotifyPlayback.device_name} (${spotifyPlayback.device_type ?? 'device'})`
                  : 'No active device reported'}
              </p>
              <div>
                <div className="ambient-progress">
                  <span style={{ width: `${progressPercent}%` }} />
                </div>
                <div className="ambient-progress-time">
                  <span>{formatDuration(spotifyPlayback.progress_ms)}</span>
                  <span>{formatDuration(spotifyPlayback.duration_ms)}</span>
                </div>
              </div>
            </div>
          )}

          {!hasPlayback && (
            <p className="ambient-empty-line">
              {isAuthenticated
                ? (spotifyPlayback?.message ??
                  'Start Spotify on one of your devices, then refresh this view.')
                : 'Spotify OAuth runs through the backend so client secrets stay out of the browser.'}
            </p>
          )}

          <div className="ambient-media-controls">
            <button
              type="button"
              onClick={() => onSpotifyAction('previous')}
              disabled={controlsDisabled}
            >
              Previous
            </button>
            <button
              type="button"
              onClick={() => onSpotifyAction(playPauseAction)}
              disabled={controlsDisabled}
            >
              {spotifyState.isLoading ? 'Working...' : playPauseLabel}
            </button>
            <button
              type="button"
              onClick={() => onSpotifyAction('next')}
              disabled={controlsDisabled}
            >
              Next
            </button>
            <button
              type="button"
              onClick={onRefresh}
              disabled={spotifyState.isLoading}
            >
              Refresh
            </button>
          </div>

          <div className="ambient-quiet-actions">
            <p>{spotifyStatus?.message ?? 'Checking Spotify connection.'}</p>
            {isConfigured && !isAuthenticated && (
              <a href={loginUrl} className="ambient-text-button">
                Connect Spotify
              </a>
            )}
            {spotifyPlayback?.spotify_url && (
              <a
                href={spotifyPlayback.spotify_url}
                target="_blank"
                rel="noreferrer"
                className="ambient-text-button"
              >
                Open in Spotify
              </a>
            )}
            {spotifyState.actionMessage && (
              <p className="ambient-success">{spotifyState.actionMessage}</p>
            )}
            {spotifyState.error && (
              <p className="ambient-warning">{spotifyState.error}</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

interface SmartHomeFocusProps {
  entities: SmartHomeEntitiesResponse | null;
  onClose: () => void;
  onEntityAction: (
    entity: SmartHomeEntity,
    action: 'turn-on' | 'turn-off',
  ) => void;
  onRefresh: () => void;
  onSceneActivate: (entity: SmartHomeEntity) => void;
  sensors: SmartHomeEntitiesResponse | null;
  smartHomeState: SmartHomeUiState;
  status: SmartHomeStatus | null;
}

function SmartHomeFocus({
  entities,
  onClose,
  onEntityAction,
  onRefresh,
  onSceneActivate,
  sensors,
  smartHomeState,
  status,
}: SmartHomeFocusProps) {
  const items = entities?.items ?? [];
  const controlItems = items.filter((entity) =>
    ['light', 'switch'].includes(entity.device_type),
  );
  const scenes = items.filter((entity) => entity.device_type === 'scene');
  const sensorItems = sensors?.items ?? [];
  const isReady = status?.enabled && status.configured;
  const title =
    status?.connection_status === 'connected' ? 'Connected Home' : 'Smart Home';

  return (
    <div className={focusPanelClass}>
      <FocusHeader eyebrow="Home" onClose={onClose} title={title} />

      <div className="ambient-quiet-actions">
        <button
          type="button"
          onClick={onRefresh}
          disabled={smartHomeState.isLoading}
          className="ambient-text-button"
        >
          {smartHomeState.isLoading ? 'Refreshing' : 'Refresh'}
        </button>
        <p>
          {status?.message ??
            'Mirrage controls Home Assistant only through backend safety rules.'}
        </p>
      </div>

      {smartHomeState.error && (
        <p className="ambient-warning">{smartHomeState.error}</p>
      )}
      {smartHomeState.actionMessage && (
        <p className="ambient-success">{smartHomeState.actionMessage}</p>
      )}

      {!isReady ? (
        <section className="ambient-onboarding">
          <p className={labelClass}>Home Assistant</p>
          <h2>
            {status?.enabled
              ? 'Add a local Home Assistant connection.'
              : 'Smart home control is off.'}
          </h2>
          <p>
            Set the smart-home environment variables on the backend. Mirrage
            will discover lights, switches, scenes, and sensors after Home
            Assistant is enabled.
          </p>
        </section>
      ) : (
        <section className="ambient-smart-home">
          <div className="ambient-smart-home-lead">
            <span>{formatStatus(status.connection_status)}</span>
            <p>
              {status.entity_count > 0
                ? `${status.entity_count} safe home item${
                    status.entity_count === 1 ? '' : 's'
                  } available.`
                : 'No supported home items were discovered yet.'}
            </p>
          </div>

          <SmartHomeEntitySection
            emptyText="No lights or switches discovered."
            entities={controlItems}
            isBusy={smartHomeState.isLoading}
            onEntityAction={onEntityAction}
            title="Lights and Switches"
          />

          <SmartHomeSceneSection
            emptyText="No scenes discovered."
            isBusy={smartHomeState.isLoading}
            onSceneActivate={onSceneActivate}
            scenes={scenes}
          />

          <SmartHomeSensorSection
            emptyText="No sensors discovered."
            sensors={sensorItems}
          />
        </section>
      )}
    </div>
  );
}

function SmartHomeEntitySection({
  emptyText,
  entities,
  isBusy,
  onEntityAction,
  title,
}: {
  emptyText: string;
  entities: SmartHomeEntity[];
  isBusy: boolean;
  onEntityAction: (
    entity: SmartHomeEntity,
    action: 'turn-on' | 'turn-off',
  ) => void;
  title: string;
}) {
  return (
    <section className="ambient-smart-home-section">
      <p className={labelClass}>{title}</p>
      {entities.length === 0 ? (
        <p className="ambient-empty-line">{emptyText}</p>
      ) : (
        <div className="ambient-home-control-list">
          {entities.map((entity) => (
            <article className="ambient-home-control" key={entity.entity_id}>
              <div>
                <h2>{entity.name}</h2>
                <p>
                  {entity.room ?? formatStatus(entity.device_type)} /{' '}
                  {formatStatus(entity.state)}
                </p>
              </div>
              <div>
                <button
                  type="button"
                  onClick={() => onEntityAction(entity, 'turn-on')}
                  disabled={isBusy || !entity.available}
                >
                  On
                </button>
                <button
                  type="button"
                  onClick={() => onEntityAction(entity, 'turn-off')}
                  disabled={isBusy || !entity.available}
                >
                  Off
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function SmartHomeSceneSection({
  emptyText,
  isBusy,
  onSceneActivate,
  scenes,
}: {
  emptyText: string;
  isBusy: boolean;
  onSceneActivate: (entity: SmartHomeEntity) => void;
  scenes: SmartHomeEntity[];
}) {
  return (
    <section className="ambient-smart-home-section">
      <p className={labelClass}>Scenes</p>
      {scenes.length === 0 ? (
        <p className="ambient-empty-line">{emptyText}</p>
      ) : (
        <div className="ambient-home-scene-list">
          {scenes.map((scene) => (
            <button
              type="button"
              key={scene.entity_id}
              onClick={() => onSceneActivate(scene)}
              disabled={isBusy || !scene.available}
            >
              <span>{scene.name}</span>
              <small>Activate</small>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}

function SmartHomeSensorSection({
  emptyText,
  sensors,
}: {
  emptyText: string;
  sensors: SmartHomeEntity[];
}) {
  return (
    <section className="ambient-smart-home-section">
      <p className={labelClass}>Sensors</p>
      {sensors.length === 0 ? (
        <p className="ambient-empty-line">{emptyText}</p>
      ) : (
        <div className="ambient-home-sensors">
          {sensors.map((sensor) => (
            <article key={sensor.entity_id}>
              <span>{sensor.name}</span>
              <strong>{formatStatus(sensor.state)}</strong>
              <small>{formatUpdated(sensor.last_updated)}</small>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

interface RelationshipFocusProps {
  directory: VisibleProfile[];
  onClose: () => void;
  onCreateRelationship: (targetUserId: string, type: string) => void;
  onCreateSharedContext: (input: {
    context_type: SharedContextItem['context_type'];
    title: string;
    value: string;
    visibility: SharedContextItem['visibility'];
  }) => void;
  onProfileUpdate: (update: PersonalizationProfileUpdate) => void;
  onRefresh: () => void;
  onRelationshipAction: (
    relationship: Relationship,
    action: 'accept' | 'reject' | 'archive',
  ) => void;
  onSharedContextAction: (
    item: SharedContextItem,
    action: 'archive' | 'share' | 'revoke',
    userId?: string,
  ) => void;
  principal: IdentityPrincipal | null;
  profile: PersonalizationProfile | null;
  relationships: Relationship[];
  sharedContext: SharedContextItem[];
  state: RelationshipUiState;
  users: IdentityUser[];
}

function RelationshipFocus({
  directory,
  onClose,
  onCreateRelationship,
  onCreateSharedContext,
  onProfileUpdate,
  onRefresh,
  onRelationshipAction,
  onSharedContextAction,
  principal,
  profile,
  relationships,
  sharedContext,
  state,
  users,
}: RelationshipFocusProps) {
  const [profileDraft, setProfileDraft] =
    useState<PersonalizationProfile | null>(profile);
  const [relationshipTarget, setRelationshipTarget] = useState('');
  const [relationshipType, setRelationshipType] = useState('friend');
  const [contextTitle, setContextTitle] = useState('');
  const [contextValue, setContextValue] = useState('');
  const [contextType, setContextType] =
    useState<SharedContextItem['context_type']>('plan');
  const [contextVisibility, setContextVisibility] =
    useState<SharedContextItem['visibility']>('private');
  const [shareTarget, setShareTarget] = useState('');

  useEffect(() => setProfileDraft(profile), [profile]);

  const availablePeople = directory.filter(
    (item) => item.user_id !== principal?.user_id,
  );
  const pendingIncoming = relationships.filter(
    (item) =>
      item.status === 'pending' &&
      item.proposed_to_user_id === principal?.user_id,
  );
  const pendingOutgoing = relationships.filter(
    (item) =>
      item.status === 'pending' &&
      item.proposed_by_user_id === principal?.user_id,
  );
  const activeRelationships = relationships.filter(
    (item) => item.status === 'active',
  );

  function personName(userId: string): string {
    const user = users.find((item) => item.public_id === userId);
    if (user) {
      return user.display_name;
    }
    const visible = directory.find((item) => item.user_id === userId);
    const name = visible?.fields.preferred_display_name;
    return typeof name === 'string' ? name : `User ${userId.slice(0, 8)}`;
  }

  function otherUser(relationship: Relationship): string {
    return relationship.user_a_id === principal?.user_id
      ? relationship.user_b_id
      : relationship.user_a_id;
  }

  function submitProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!profileDraft) {
      return;
    }
    onProfileUpdate({
      preferred_display_name: profileDraft.preferred_display_name,
      preferred_language: profileDraft.preferred_language,
      response_tone: profileDraft.response_tone,
      response_length: profileDraft.response_length,
      greeting_style: profileDraft.greeting_style,
      humour: profileDraft.humour,
      proactivity: profileDraft.proactivity,
      quiet_hours_start: profileDraft.quiet_hours_start,
      quiet_hours_end: profileDraft.quiet_hours_end,
      time_zone: profileDraft.time_zone,
      spoken_announcements: profileDraft.spoken_announcements,
      personalized_greeting: profileDraft.personalized_greeting,
      cloud_personalization_opt_in: profileDraft.cloud_personalization_opt_in,
      visibility: profileDraft.visibility,
    });
  }

  function submitRelationship(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (relationshipTarget) {
      onCreateRelationship(relationshipTarget, relationshipType);
    }
  }

  function submitContext(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!contextTitle.trim() || !contextValue.trim()) {
      return;
    }
    onCreateSharedContext({
      context_type: contextType,
      title: contextTitle.trim(),
      value: contextValue.trim(),
      visibility: contextVisibility,
    });
    setContextTitle('');
    setContextValue('');
  }

  if (!principal) {
    return (
      <div className={focusPanelClass}>
        <FocusHeader eyebrow="Personal" onClose={onClose} title="Profile" />
        <p className="ambient-empty-line">
          Authenticate a trusted device from Identity before opening private
          preferences.
        </p>
      </div>
    );
  }

  return (
    <div className={`${focusPanelClass} ambient-relationships`}>
      <FocusHeader
        eyebrow="Personal"
        onClose={onClose}
        title="Profile & Relationships"
      />

      {!profileDraft ? (
        <section className="ambient-profile-intro">
          <p className={labelClass}>Private by default</p>
          <h2>Activate your human session to continue.</h2>
          <p>
            A trusted mirror token identifies the device, not the person in
            front of it. Open Identity to make a temporary user selection.
          </p>
        </section>
      ) : (
        <>
          <form className="ambient-profile-form" onSubmit={submitProfile}>
            <section>
              <p className={labelClass}>My Profile</p>
              <div className="ambient-profile-fields">
                <label>
                  Preferred name
                  <input
                    value={profileDraft.preferred_display_name}
                    onChange={(event) =>
                      setProfileDraft({
                        ...profileDraft,
                        preferred_display_name: event.target.value,
                      })
                    }
                  />
                </label>
                <label>
                  Language
                  <input
                    value={profileDraft.preferred_language}
                    onChange={(event) =>
                      setProfileDraft({
                        ...profileDraft,
                        preferred_language: event.target.value,
                      })
                    }
                  />
                </label>
                <ProfileSelect
                  label="Tone"
                  value={profileDraft.response_tone}
                  values={['neutral', 'direct', 'warm', 'formal']}
                  onChange={(value) =>
                    setProfileDraft({
                      ...profileDraft,
                      response_tone:
                        value as PersonalizationProfile['response_tone'],
                    })
                  }
                />
                <ProfileSelect
                  label="Response length"
                  value={profileDraft.response_length}
                  values={['concise', 'balanced', 'detailed']}
                  onChange={(value) =>
                    setProfileDraft({
                      ...profileDraft,
                      response_length:
                        value as PersonalizationProfile['response_length'],
                    })
                  }
                />
                <ProfileSelect
                  label="Greeting"
                  value={profileDraft.greeting_style}
                  values={['none', 'minimal', 'standard', 'warm']}
                  onChange={(value) =>
                    setProfileDraft({
                      ...profileDraft,
                      greeting_style:
                        value as PersonalizationProfile['greeting_style'],
                    })
                  }
                />
                <ProfileSelect
                  label="Proactivity"
                  value={profileDraft.proactivity}
                  values={['silent', 'low', 'standard', 'high']}
                  onChange={(value) =>
                    setProfileDraft({
                      ...profileDraft,
                      proactivity:
                        value as PersonalizationProfile['proactivity'],
                    })
                  }
                />
                <label>
                  Quiet from
                  <input
                    type="time"
                    value={profileDraft.quiet_hours_start ?? ''}
                    onChange={(event) =>
                      setProfileDraft({
                        ...profileDraft,
                        quiet_hours_start: event.target.value || null,
                      })
                    }
                  />
                </label>
                <label>
                  Quiet until
                  <input
                    type="time"
                    value={profileDraft.quiet_hours_end ?? ''}
                    onChange={(event) =>
                      setProfileDraft({
                        ...profileDraft,
                        quiet_hours_end: event.target.value || null,
                      })
                    }
                  />
                </label>
              </div>
              <div className="ambient-profile-toggles">
                <ProfileToggle
                  checked={profileDraft.personalized_greeting}
                  label="Personalized greeting"
                  onChange={(checked) =>
                    setProfileDraft({
                      ...profileDraft,
                      personalized_greeting: checked,
                    })
                  }
                />
                <ProfileToggle
                  checked={profileDraft.spoken_announcements}
                  label="Spoken announcements"
                  onChange={(checked) =>
                    setProfileDraft({
                      ...profileDraft,
                      spoken_announcements: checked,
                    })
                  }
                />
                <ProfileToggle
                  checked={profileDraft.cloud_personalization_opt_in}
                  label="Cloud-safe personalization"
                  onChange={(checked) =>
                    setProfileDraft({
                      ...profileDraft,
                      cloud_personalization_opt_in: checked,
                    })
                  }
                />
              </div>
            </section>

            <section className="ambient-profile-privacy">
              <p className={labelClass}>Privacy Visibility</p>
              <p>
                Private is the default. Relationship labels never grant system
                permissions.
              </p>
              {[
                'preferred_display_name',
                'preferred_language',
                'response_tone',
                'response_length',
              ].map((field) => (
                <ProfileSelect
                  key={field}
                  label={formatStatus(field)}
                  value={profileDraft.visibility[field] ?? 'private'}
                  values={['private', 'relationship', 'household', 'public']}
                  onChange={(value) =>
                    setProfileDraft({
                      ...profileDraft,
                      visibility: {
                        ...profileDraft.visibility,
                        [field]: value as SharedContextItem['visibility'],
                      },
                    })
                  }
                />
              ))}
            </section>
            <button type="submit" disabled={state.isLoading}>
              Save preferences
            </button>
          </form>

          <section className="ambient-relationship-section">
            <p className={labelClass}>Relationships</p>
            <form className="ambient-inline-form" onSubmit={submitRelationship}>
              <select
                value={relationshipTarget}
                onChange={(event) => setRelationshipTarget(event.target.value)}
                aria-label="Relationship user"
              >
                <option value="">Choose a user</option>
                {availablePeople.map((person) => (
                  <option key={person.user_id} value={person.user_id}>
                    {personName(person.user_id)}
                  </option>
                ))}
              </select>
              <select
                value={relationshipType}
                onChange={(event) => setRelationshipType(event.target.value)}
                aria-label="Relationship type"
              >
                {[
                  'partner',
                  'parent',
                  'child',
                  'sibling',
                  'relative',
                  'friend',
                  'close_friend',
                  'colleague',
                  'housemate',
                  'caregiver',
                  'household_member',
                ].map((type) => (
                  <option key={type} value={type}>
                    {formatStatus(type)}
                  </option>
                ))}
              </select>
              <button type="submit" disabled={!relationshipTarget}>
                Request confirmation
              </button>
            </form>

            <RelationshipList
              empty="No active relationships."
              items={activeRelationships}
              personName={personName}
              otherUser={otherUser}
              onAction={onRelationshipAction}
            />
            {pendingIncoming.length > 0 && (
              <RelationshipList
                empty=""
                items={pendingIncoming}
                personName={personName}
                otherUser={otherUser}
                onAction={onRelationshipAction}
                pendingIncoming
              />
            )}
            {pendingOutgoing.length > 0 && (
              <p className="ambient-empty-line">
                {pendingOutgoing.length} request
                {pendingOutgoing.length === 1 ? '' : 's'} waiting for consent.
              </p>
            )}
          </section>

          <section className="ambient-relationship-section">
            <p className={labelClass}>Shared Context</p>
            <p>
              Use this only for non-sensitive plans, reminders, household facts,
              projects, or preferences. Every item has an owner.
            </p>
            <form className="ambient-context-form" onSubmit={submitContext}>
              <input
                value={contextTitle}
                onChange={(event) => setContextTitle(event.target.value)}
                placeholder="Title"
                maxLength={160}
              />
              <textarea
                value={contextValue}
                onChange={(event) => setContextValue(event.target.value)}
                placeholder="Context"
                maxLength={2000}
              />
              <div>
                <select
                  value={contextType}
                  onChange={(event) =>
                    setContextType(
                      event.target.value as SharedContextItem['context_type'],
                    )
                  }
                >
                  {['plan', 'reminder', 'fact', 'project', 'preference'].map(
                    (type) => (
                      <option key={type}>{type}</option>
                    ),
                  )}
                </select>
                <select
                  value={contextVisibility}
                  onChange={(event) =>
                    setContextVisibility(
                      event.target.value as SharedContextItem['visibility'],
                    )
                  }
                >
                  {['private', 'relationship', 'household', 'public'].map(
                    (visibility) => (
                      <option key={visibility}>{visibility}</option>
                    ),
                  )}
                </select>
                <button type="submit">Create private-first context</button>
              </div>
            </form>

            <div className="ambient-shared-list">
              {sharedContext.length === 0 ? (
                <p className="ambient-empty-line">No shared context exists.</p>
              ) : (
                sharedContext.map((item) => (
                  <article key={item.public_id}>
                    <div>
                      <small>
                        {formatStatus(item.context_type)} /{' '}
                        {formatStatus(item.visibility)}
                      </small>
                      <h3>{item.title}</h3>
                      <p>{item.value}</p>
                    </div>
                    {item.owner_user_id === principal.user_id && (
                      <div className="ambient-quiet-actions">
                        <select
                          value={shareTarget}
                          onChange={(event) =>
                            setShareTarget(event.target.value)
                          }
                          aria-label="Share with user"
                        >
                          <option value="">Choose user</option>
                          {availablePeople.map((person) => (
                            <option key={person.user_id} value={person.user_id}>
                              {personName(person.user_id)}
                            </option>
                          ))}
                        </select>
                        <button
                          type="button"
                          disabled={!shareTarget}
                          onClick={() =>
                            onSharedContextAction(item, 'share', shareTarget)
                          }
                        >
                          Share
                        </button>
                        {item.shared_with_user_ids.map((userId) => (
                          <button
                            key={userId}
                            type="button"
                            onClick={() =>
                              onSharedContextAction(item, 'revoke', userId)
                            }
                          >
                            Revoke {personName(userId)}
                          </button>
                        ))}
                        <button
                          type="button"
                          onClick={() => onSharedContextAction(item, 'archive')}
                        >
                          Archive
                        </button>
                      </div>
                    )}
                  </article>
                ))
              )}
            </div>
          </section>

          <section className="ambient-relationship-section">
            <p className={labelClass}>Household Directory</p>
            <p>
              Only fields each person made visible are shown. Account ownership
              does not reveal private profile fields.
            </p>
            <div className="ambient-directory">
              {directory.map((person) => (
                <p key={person.user_id}>
                  <strong>{personName(person.user_id)}</strong>{' '}
                  <span>
                    {person.visible_fields.map(formatStatus).join(', ')}
                  </span>
                </p>
              ))}
            </div>
          </section>
        </>
      )}

      <div className="ambient-quiet-actions">
        <button type="button" onClick={onRefresh}>
          Refresh
        </button>
      </div>
      {state.message && <p className="ambient-success">{state.message}</p>}
      {state.error && <p className="ambient-warning">{state.error}</p>}
    </div>
  );
}

function ProfileSelect({
  label,
  onChange,
  value,
  values,
}: {
  label: string;
  onChange: (value: string) => void;
  value: string;
  values: string[];
}) {
  return (
    <label>
      {label}
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {values.map((item) => (
          <option key={item} value={item}>
            {formatStatus(item)}
          </option>
        ))}
      </select>
    </label>
  );
}

function ProfileToggle({
  checked,
  label,
  onChange,
}: {
  checked: boolean;
  label: string;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label>
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
      />
      {label}
    </label>
  );
}

function RelationshipList({
  empty,
  items,
  onAction,
  otherUser,
  pendingIncoming = false,
  personName,
}: {
  empty: string;
  items: Relationship[];
  onAction: (
    relationship: Relationship,
    action: 'accept' | 'reject' | 'archive',
  ) => void;
  otherUser: (relationship: Relationship) => string;
  pendingIncoming?: boolean;
  personName: (userId: string) => string;
}) {
  if (items.length === 0) {
    return empty ? <p className="ambient-empty-line">{empty}</p> : null;
  }
  return (
    <div className="ambient-relationship-list">
      {items.map((relationship) => (
        <article key={relationship.public_id}>
          <div>
            <h3>{personName(otherUser(relationship))}</h3>
            <p>{formatStatus(relationship.relationship_type)}</p>
          </div>
          <div className="ambient-quiet-actions">
            {pendingIncoming ? (
              <>
                <button
                  type="button"
                  onClick={() => onAction(relationship, 'accept')}
                >
                  Accept
                </button>
                <button
                  type="button"
                  onClick={() => onAction(relationship, 'reject')}
                >
                  Reject
                </button>
              </>
            ) : (
              <button
                type="button"
                onClick={() => onAction(relationship, 'archive')}
              >
                Archive
              </button>
            )}
          </div>
        </article>
      ))}
    </div>
  );
}

interface IdentityFocusProps {
  auditEvents: AuditEvent[];
  devices: TrustedDevice[];
  identityState: IdentityUiState;
  onActivateHumanSession: () => void;
  onClose: () => void;
  onDisableUser: (user: IdentityUser) => void;
  onDisconnect: () => void;
  onEndHumanSession: () => void;
  onRefresh: () => void;
  onRevokeDevice: (device: TrustedDevice) => void;
  onTokenChange: (value: string) => void;
  onTokenSubmit: (event: FormEvent<HTMLFormElement>) => void;
  pendingApprovals: Approval[];
  principal: IdentityPrincipal | null;
  tokenDraft: string;
  users: IdentityUser[];
}

function IdentityFocus({
  auditEvents,
  devices,
  identityState,
  onActivateHumanSession,
  onClose,
  onDisableUser,
  onDisconnect,
  onEndHumanSession,
  onRefresh,
  onRevokeDevice,
  onTokenChange,
  onTokenSubmit,
  pendingApprovals,
  principal,
  tokenDraft,
  users,
}: IdentityFocusProps) {
  const isOwner = principal?.role === 'owner';

  return (
    <div className={focusPanelClass}>
      <FocusHeader
        eyebrow="Safety"
        onClose={onClose}
        title="Household Identity"
      />

      {!principal ? (
        <section className="ambient-identity-login">
          <p className={labelClass}>Trusted Device</p>
          <h2>Authenticate this browser session.</h2>
          <p>
            Use a device token issued by the backend. It stays in memory and is
            cleared when this page closes.
          </p>
          <form onSubmit={onTokenSubmit}>
            <input
              type="password"
              value={tokenDraft}
              onChange={(event) => onTokenChange(event.target.value)}
              placeholder="mrg_..."
              autoComplete="off"
              spellCheck={false}
              aria-label="Trusted-device token"
            />
            <button type="submit" disabled={!tokenDraft.trim()}>
              Authenticate
            </button>
          </form>
        </section>
      ) : (
        <div className="ambient-identity">
          <section className="ambient-identity-current">
            <p className={labelClass}>Active Identity</p>
            <h2>{principal.display_name}</h2>
            <p>
              {formatStatus(principal.role)} /{' '}
              {formatStatus(principal.authentication_method)} /{' '}
              {formatStatus(principal.assurance_level)} assurance /{' '}
              {principal.human_session_active
                ? 'human session active'
                : 'device identity only'}
            </p>
            {!principal.human_session_active &&
              principal.authentication_method === 'trusted_device' && (
                <p>
                  Activating a user is an explicit temporary selection. It does
                  not claim biometric or voice identity proof.
                </p>
              )}
            <div className="ambient-quiet-actions">
              <button type="button" onClick={onRefresh}>
                Refresh
              </button>
              {!principal.human_session_active &&
                principal.authentication_method === 'trusted_device' && (
                  <button type="button" onClick={onActivateHumanSession}>
                    Activate selected user
                  </button>
                )}
              {principal.human_session_active &&
                principal.authentication_method === 'trusted_device' && (
                  <button type="button" onClick={onEndHumanSession}>
                    End human session
                  </button>
                )}
              <button type="button" onClick={onDisconnect}>
                Forget device token
              </button>
            </div>
          </section>

          {isOwner ? (
            <>
              <IdentityListSection title="Household Users">
                {users.map((user) => (
                  <article key={user.public_id}>
                    <div>
                      <h3>{user.display_name}</h3>
                      <p>
                        {formatStatus(user.role)} / {formatStatus(user.status)}
                      </p>
                    </div>
                    {user.status === 'active' && user.role !== 'owner' && (
                      <button
                        type="button"
                        onClick={() => onDisableUser(user)}
                        disabled={identityState.isLoading}
                      >
                        Disable
                      </button>
                    )}
                  </article>
                ))}
              </IdentityListSection>

              <IdentityListSection title="Trusted Devices">
                {devices.map((device) => (
                  <article key={device.public_id}>
                    <div>
                      <h3>{device.display_name}</h3>
                      <p>
                        {formatStatus(device.device_type)} /{' '}
                        {formatStatus(device.trust_level)} /{' '}
                        {formatStatus(device.status)}
                      </p>
                    </div>
                    {device.status === 'active' &&
                      device.public_id !== principal.device_id && (
                        <button
                          type="button"
                          onClick={() => onRevokeDevice(device)}
                          disabled={identityState.isLoading}
                        >
                          Revoke
                        </button>
                      )}
                  </article>
                ))}
              </IdentityListSection>

              <IdentityListSection title="Pending Approvals">
                {pendingApprovals.length === 0 ? (
                  <p>No requests are waiting for review.</p>
                ) : (
                  pendingApprovals.map((approval) => (
                    <article key={approval.public_id}>
                      <div>
                        <h3>{formatStatus(approval.action)}</h3>
                        <p>
                          {formatStatus(approval.risk_level)} / expires{' '}
                          {formatUpdated(approval.expires_at)}
                        </p>
                      </div>
                    </article>
                  ))
                )}
              </IdentityListSection>

              <IdentityListSection title="Recent Audit Events">
                {auditEvents.map((event) => (
                  <article key={event.public_id}>
                    <div>
                      <h3>{formatStatus(event.event_type)}</h3>
                      <p>
                        {formatUpdated(event.timestamp)} /{' '}
                        {formatStatus(
                          event.result ?? event.authorization_decision ?? '',
                        )}
                      </p>
                    </div>
                  </article>
                ))}
              </IdentityListSection>
            </>
          ) : (
            <p className="ambient-empty-line">
              Household administration is available to owners only.
            </p>
          )}
        </div>
      )}

      {identityState.message && (
        <p className="ambient-success">{identityState.message}</p>
      )}
      {identityState.error && (
        <p className="ambient-warning">{identityState.error}</p>
      )}
    </div>
  );
}

function IdentityListSection({
  children,
  title,
}: {
  children: ReactNode;
  title: string;
}) {
  return (
    <section className="ambient-identity-section">
      <p className={labelClass}>{title}</p>
      <div className="ambient-identity-list">{children}</div>
    </section>
  );
}

interface FocusHeaderProps {
  eyebrow: string;
  onClose: () => void;
  title: string;
}

function FocusHeader({ eyebrow, onClose, title }: FocusHeaderProps) {
  return (
    <header className="ambient-focus-header">
      <div>
        <p className={labelClass}>{eyebrow}</p>
        <h1>{title}</h1>
      </div>
      <button type="button" onClick={onClose} className="ambient-close">
        Close
      </button>
    </header>
  );
}
