import type { AgentRun } from '../types';

interface AgentRunListProps {
  activeRunId: string | null;
  onSelect: (runId: string) => void;
  runs: AgentRun[];
}

export function AgentRunList({
  activeRunId,
  onSelect,
  runs,
}: AgentRunListProps) {
  return (
    <section className="agent-run-list" aria-label="Agent runs">
      <p className="agent-section-label">Recent tasks</p>
      {runs.length === 0 ? (
        <p className="agent-muted">No agent tasks yet.</p>
      ) : (
        <div>
          {runs.map((run) => (
            <button
              type="button"
              className={run.public_id === activeRunId ? 'is-active' : ''}
              key={run.public_id}
              onClick={() => onSelect(run.public_id)}
            >
              <span>{run.goal}</span>
              <small>{run.status.replaceAll('_', ' ')}</small>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}
