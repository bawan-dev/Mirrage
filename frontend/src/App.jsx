import { useEffect, useMemo, useState } from 'react';

export default function App() {
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const timer = window.setInterval(() => {
      setNow(new Date());
    }, 1000);

    return () => window.clearInterval(timer);
  }, []);

  const currentTime = useMemo(
    () =>
      new Intl.DateTimeFormat('en-GB', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
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

  return (
    <main className="mirror-dashboard">
      <section className="hero-panel" aria-labelledby="dashboard-title">
        <p className="eyebrow">Mirrage</p>
        <h1 id="dashboard-title">Smart Mirror Dashboard</h1>
        <p>Dashboard online. Local frontend session active.</p>
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
          <strong>Not listening</strong>
          <p>Microphone input inactive.</p>
        </article>

        <article className="dashboard-card">
          <span>System</span>
          <strong>Starting</strong>
          <p>Frontend running locally.</p>
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
