import { useEffect, useMemo, useState } from 'react';

import { getHealthStatus, getSystemStatus, getVoiceStatus } from './api.js';

function formatStatus(value) {
  if (!value) {
    return 'Unknown';
  }

  return value
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export default function App() {
  const [now, setNow] = useState(() => new Date());
  const [healthStatus, setHealthStatus] = useState(null);
  const [systemStatus, setSystemStatus] = useState(null);
  const [voiceStatus, setVoiceStatus] = useState(null);
  const [backendState, setBackendState] = useState({
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
    <main className="mirror-dashboard">
      <section className="hero-panel" aria-labelledby="dashboard-title">
        <p className="eyebrow">Mirrage</p>
        <h1 id="dashboard-title">Smart Mirror Dashboard</h1>
        <p>{sessionMessage}</p>
      </section>

      <section className="dashboard-grid" aria-label="Dashboard cards">
        <article className="dashboard-card">
          <span>Time</span>
          <strong>{currentTime}</strong>
          <p>{currentDate}</p>
        </article>

        <article className="dashboard-card">
          <span>Weather</span>
          <strong>Forecast pending</strong>
          <p>Local provider not connected.</p>
        </article>

        <article className="dashboard-card">
          <span>Assistant</span>
          <strong>Standby</strong>
          <p>Assistant route not connected.</p>
        </article>

        <article className="dashboard-card">
          <span>Voice</span>
          <strong>{voiceTitle}</strong>
          <p>{voiceDetail}</p>
        </article>

        <article className="dashboard-card">
          <span>System</span>
          <strong>{systemTitle}</strong>
          <p>{systemDetail}</p>
        </article>

        <article className="dashboard-card">
          <span>Hardware</span>
          <strong>Planning</strong>
          <p>Mirror hardware not connected.</p>
        </article>
      </section>
    </main>
  );
}
