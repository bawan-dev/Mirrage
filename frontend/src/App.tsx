import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react';

import {
  getHealthStatus,
  getSystemStatus,
  getVoiceStatus,
  getWeather,
  sendAssistantMessage,
} from './api';
import type {
  AssistantReply,
  HealthStatus,
  SystemStatus,
  VoiceStatus,
  WeatherInfo,
} from './types';

type FocusView = 'home' | 'weather' | 'assistant' | 'media';

interface BackendState {
  error: string | null;
  isLoading: boolean;
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
  'animate-focus-in rounded-xl border border-line bg-panel p-5 shadow-mirror md:p-8';

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
  const [activeView, setActiveView] = useState<FocusView>('home');
  const recognitionRef = useRef<BrowserSpeechRecognition | null>(null);
  const [now, setNow] = useState<Date>(() => new Date());
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [voiceStatus, setVoiceStatus] = useState<VoiceStatus | null>(null);
  const [weather, setWeather] = useState<WeatherInfo | null>(null);
  const [backendState, setBackendState] = useState<BackendState>({
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
  const [assistantMessages, setAssistantMessages] = useState<
    AssistantMessage[]
  >([
    {
      role: 'assistant',
      text: 'Assistant route is ready. Real responses depend on the configured provider.',
      meta: 'Provider status appears after the first message.',
    },
  ]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setNow(new Date());
    }, 1000);

    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    setVoiceSupported(getSpeechRecognitionConstructor() !== null);

    return () => {
      recognitionRef.current?.abort();
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

  async function sendAssistantRequest(
    message: string,
    source: 'typed' | 'voice',
  ) {
    if (!message || assistantBusy) {
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
    recognitionRef.current?.stop();
  }

  function openFocus(view: Exclude<FocusView, 'home'>) {
    setActiveView(view);
  }

  function closeFocus() {
    setActiveView('home');
  }

  return (
    <main className="relative mx-auto flex min-h-screen w-[min(1180px,100%)] flex-col justify-center overflow-hidden px-4 py-8 md:px-8">
      <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(circle_at_20%_20%,rgba(109,215,232,0.10),transparent_28%),radial-gradient(circle_at_85%_70%,rgba(122,217,165,0.08),transparent_28%)]" />

      <section
        className={`transition-all duration-500 ${
          activeView === 'home'
            ? 'translate-y-0 opacity-100'
            : 'pointer-events-none -translate-y-4 opacity-0 blur-sm'
        }`}
        aria-hidden={activeView !== 'home'}
      >
        <HomeState
          backendLabel={backendLabel}
          currentDate={currentDate}
          currentTime={currentTime}
          onOpen={openFocus}
          systemLabel={systemLabel}
          voiceLabel={voiceLabel}
          weather={weather}
          weatherSummary={weatherSummary}
        />
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
            assistantBusy={assistantBusy}
            assistantError={assistantError}
            assistantMessages={assistantMessages}
            assistantProvider={assistantProvider}
            draft={draft}
            microphoneReady={microphoneReady}
            onClose={closeFocus}
            onDraftChange={setDraft}
            onStartVoice={startVoiceCapture}
            onStopVoice={stopVoiceCapture}
            onSubmit={handleAssistantSubmit}
            voiceError={voiceError}
            voiceInterimTranscript={voiceInterimTranscript}
            voiceListening={voiceListening}
            voiceSupported={voiceSupported}
            voiceTranscript={voiceTranscript}
          />
        )}

        {activeView === 'media' && <MediaFocus onClose={closeFocus} />}
      </section>
    </main>
  );
}

interface HomeStateProps {
  backendLabel: string;
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
        className="grid grid-cols-1 gap-4 md:grid-cols-3"
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
            Open a focused assistant view and send a typed request.
          </p>
        </button>

        <button
          type="button"
          className={focusButtonBase}
          onClick={() => onOpen('media')}
        >
          <span className={labelClass}>Media</span>
          <strong className="mt-8 block text-4xl font-semibold text-text">
            Planned
          </strong>
          <p className={`mt-3 ${mutedClass}`}>
            Mock controls only. No Spotify account is connected yet.
          </p>
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

interface AssistantFocusProps {
  assistantBusy: boolean;
  assistantError: string | null;
  assistantMessages: AssistantMessage[];
  assistantProvider: string | null;
  draft: string;
  microphoneReady: boolean;
  onClose: () => void;
  onDraftChange: (value: string) => void;
  onStartVoice: () => void;
  onStopVoice: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  voiceError: string | null;
  voiceInterimTranscript: string;
  voiceListening: boolean;
  voiceSupported: boolean;
  voiceTranscript: string;
}

function AssistantFocus({
  assistantBusy,
  assistantError,
  assistantMessages,
  assistantProvider,
  draft,
  microphoneReady,
  onClose,
  onDraftChange,
  onStartVoice,
  onStopVoice,
  onSubmit,
  voiceError,
  voiceInterimTranscript,
  voiceListening,
  voiceSupported,
  voiceTranscript,
}: AssistantFocusProps) {
  const voiceButtonLabel = voiceListening ? 'Stop listening' : 'Push to talk';

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
  onClose: () => void;
}

function MediaFocus({ onClose }: MediaFocusProps) {
  return (
    <div className={focusPanelClass}>
      <FocusHeader
        eyebrow="Media Focus"
        onClose={onClose}
        title="Music mockup"
      />

      <div className="mt-10 grid items-center gap-8 md:grid-cols-[320px_1fr]">
        <div className="aspect-square rounded-xl border border-line bg-[linear-gradient(135deg,rgba(109,215,232,0.24),rgba(122,217,165,0.10),rgba(240,195,106,0.16))] shadow-mirror" />

        <div>
          <p className={labelClass}>Planned Spotify-style integration</p>
          <h2 className="mt-4 text-4xl font-semibold text-text md:text-6xl">
            Late Night Build
          </h2>
          <p className="mt-4 text-xl text-muted">Mock Artist</p>
          <p className={`mt-8 max-w-xl ${mutedClass}`}>
            This view is only a UI placeholder. No Spotify API, account login,
            playback, or device control is connected yet.
          </p>

          <div className="mt-8 flex flex-wrap gap-3">
            {['Previous', 'Play', 'Next'].map((action) => (
              <button
                type="button"
                className="rounded-full border border-line bg-panel-strong px-5 py-3 text-sm font-semibold text-text transition hover:border-cyan/70 hover:text-cyan"
                key={action}
              >
                {action}
              </button>
            ))}
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
