import type { AgentEvent, AgentRun } from '../types';

interface AgentResultViewProps {
  events: AgentEvent[];
  run: AgentRun;
}

export function AgentResultView({ events, run }: AgentResultViewProps) {
  return (
    <section className="agent-result-view">
      {run.final_result && (
        <>
          <p className="agent-section-label">Result</p>
          <p className="agent-final-result">{run.final_result}</p>
        </>
      )}
      {run.error_summary && (
        <p className="agent-error-text">{run.error_summary}</p>
      )}
      {events.length > 0 && (
        <div className="agent-event-history">
          <p className="agent-section-label">Safe execution history</p>
          {events.map((event) => (
            <p key={event.public_id}>
              <span>{event.event_type.replaceAll('_', ' ')}</span>
              {event.message}
            </p>
          ))}
        </div>
      )}
    </section>
  );
}
