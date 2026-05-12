export default function App() {
  return (
    <main className="mirror-dashboard">
      <section className="hero-panel" aria-labelledby="dashboard-title">
        <p className="eyebrow">Mirrage</p>
        <h1 id="dashboard-title">Smart Mirror Dashboard</h1>
        <p>
          A focused home display for time, status, voice, and assistant
          interaction.
        </p>
      </section>

      <section className="dashboard-grid" aria-label="Dashboard cards">
        <article className="dashboard-card">
          <span>Time</span>
          <strong>--:--</strong>
          <p>Date and clock display will be added next.</p>
        </article>

        <article className="dashboard-card">
          <span>Weather</span>
          <strong>Planned</strong>
          <p>Local weather data will connect later.</p>
        </article>

        <article className="dashboard-card">
          <span>Assistant</span>
          <strong>Ready to wire</strong>
          <p>The assistant card will connect to the backend API.</p>
        </article>

        <article className="dashboard-card">
          <span>Voice</span>
          <strong>Not listening</strong>
          <p>Voice status will start as a backend status check.</p>
        </article>

        <article className="dashboard-card">
          <span>System</span>
          <strong>Starting</strong>
          <p>System state will come from the FastAPI backend.</p>
        </article>

        <article className="dashboard-card">
          <span>Hardware</span>
          <strong>Planning</strong>
          <p>Display, mirror, microphone, and sensor notes live in hardware docs.</p>
        </article>
      </section>
    </main>
  );
}
