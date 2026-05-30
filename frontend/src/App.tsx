import { useEffect, useMemo, useState } from 'react';

import { getHealthStatus, getSystemStatus, getVoiceStatus } from './api';
import type { HealthStatus, SystemStatus, VoiceStatus } from './types';

interface BackendState {
  error: string | null;
  isLoading: boolean;
}

function formatStatus(value?: string): string {
  if (!value) {
    return 'Unknown';
  }

  return value
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

const cardBase =
  'flex min-h-[180px] flex-col justify-between gap-5 rounded-lg border border-line bg-panel p-[22px] shadow-mirror';
const labelClass = 'text-[0.78rem] font-bold uppercase text-cyan';
const valueClass = 'block text-[1.75rem] font-bold leading-tight text-text';
const detailClass = 'leading-snug text-muted';

export default function App() {
  const [now, setNow] = useState<Date>(() => new Date());
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [voiceStatus, setVoiceStatus] = useState<VoiceStatus | null>(null);
  const [backendState, setBackendState] = useState<BackendState>({
    error: null,
    isLoading: true,
  });

  useEffect(() => {
    const timer = window.setInterval(() => {
      setNow(new Date());
    }, 1000);

    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    let isActive = true;

    async function loadBackendStatus() {
      try {
        const [health, system, voice] = await Promise.all([
          getHealthStatus(),
          getSystemStatus(),
          getVoiceStatus(),
        ]);

        if (!isActive) {
          return;
        }

        setHealthStatus(health);
        setSystemStatus(system);
        setVoiceStatus(voice);
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

  const sessionMessage = useMemo(() => {
    if (backendState.isLoading) {
      return 'Dashboard online. Checking backend session.';
    }

    if (backendState.error) {
      return 'Dashboard online. Backend unavailable.';
    }

    return `Dashboard online. Backend ${formatStatus(healthStatus?.status)}.`;
  }, [backendState.error, backendState.isLoading, healthStatus]);

  const systemTitle = useMemo(() => {
    if (backendState.isLoading) {
      return 'Checking';
    }

    if (backendState.error) {
      return 'Offline';
    }

    return formatStatus(systemStatus?.status);
  }, [backendState.error, backendState.isLoading, systemStatus]);

  const systemDetail = useMemo(() => {
    if (backendState.isLoading) {
      return 'Reading backend status.';
    }

    if (backendState.error) {
      return 'Backend status unavailable.';
    }

    return `Backend ${formatStatus(systemStatus?.backend)}. AI ${formatStatus(
      systemStatus?.ai,
    )}.`;
  }, [backendState.error, backendState.isLoading, systemStatus]);

  const voiceTitle = useMemo(() => {
    if (backendState.isLoading) {
      return 'Checking';
    }

    if (backendState.error) {
      return 'Unknown';
    }

    return voiceStatus?.listening ? 'Listening' : 'Not listening';
  }, [backendState.error, backendState.isLoading, voiceStatus]);

  const voiceDetail = useMemo(() => {
    if (backendState.isLoading) {
      return 'Reading voice state.';
    }

    if (backendState.error) {
      return 'Voice status unavailable.';
    }

    return `Wake word ${formatStatus(voiceStatus?.wake_word)}.`;
  }, [backendState.error, backendState.isLoading, voiceStatus]);

  return (
    <main className="mx-auto grid min-h-screen w-[min(1120px,100%)] content-start gap-[22px] px-4 py-7 md:content-center md:px-6 md:py-12">
      <section
        className="panel-hero rounded-lg border border-line p-6 shadow-mirror md:p-8"
        aria-labelledby="dashboard-title"
      >
        <p className={labelClass}>Mirrage</p>
        <h1
          id="dashboard-title"
          className="mt-3.5 text-[2rem] font-bold leading-none sm:text-[2.45rem] md:text-[3.6rem]"
        >
          Smart Mirror Dashboard
        </h1>
        <p className="mt-[18px] max-w-[680px] text-[1.08rem] leading-relaxed text-muted">
          {sessionMessage}
        </p>
      </section>

      <section
        className="grid grid-cols-1 gap-4 md:grid-cols-6"
        aria-label="Dashboard cards"
      >
        <article className={`${cardBase} panel-time md:col-span-4`}>
          <span className={labelClass}>Time</span>
          <strong className="block text-[1.65rem] font-bold leading-none tabular-nums text-text sm:text-[3rem] md:text-[4rem]">
            {currentTime}
          </strong>
          <p className={detailClass}>{currentDate}</p>
        </article>

        <article className={`${cardBase} md:col-span-2`}>
          <span className={labelClass}>Weather</span>
          <strong className={`${valueClass} text-amber`}>Forecast pending</strong>
          <p className={detailClass}>Local provider not connected.</p>
        </article>

        <article className={`${cardBase} md:col-span-2`}>
          <span className={labelClass}>Assistant</span>
          <strong className={`${valueClass} text-green`}>Standby</strong>
          <p className={detailClass}>Assistant route not connected.</p>
        </article>

        <article className={`${cardBase} md:col-span-2`}>
          <span className={labelClass}>Voice</span>
          <strong className={valueClass}>{voiceTitle}</strong>
          <p className={detailClass}>{voiceDetail}</p>
        </article>

        <article className={`${cardBase} md:col-span-2`}>
          <span className={labelClass}>System</span>
          <strong className={`${valueClass} text-green`}>{systemTitle}</strong>
          <p className={detailClass}>{systemDetail}</p>
        </article>

        <article className={`${cardBase} min-h-[140px] md:col-span-6`}>
          <span className={labelClass}>Hardware</span>
          <strong className={valueClass}>Planning</strong>
          <p className={detailClass}>Mirror hardware not connected.</p>
        </article>
      </section>
    </main>
  );
}
