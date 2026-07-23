import type { AgentRunDetail } from '../types';
import { AgentStepTimeline } from './AgentStepTimeline';

interface AgentPlanViewProps {
  detail: AgentRunDetail;
}

export function AgentPlanView({ detail }: AgentPlanViewProps) {
  return (
    <section className="agent-plan-view">
      <div className="agent-run-heading">
        <p className="agent-section-label">
          {detail.run.agent_type.replace('_', ' ')} agent
        </p>
        <h2>{detail.run.goal}</h2>
        <span>{detail.run.status.replaceAll('_', ' ')}</span>
      </div>

      {detail.run.clarification_prompt && (
        <p className="agent-clarification">{detail.run.clarification_prompt}</p>
      )}

      {detail.run.assumptions.length > 0 && (
        <div className="agent-assumptions">
          <p className="agent-section-label">Boundaries</p>
          {detail.run.assumptions.map((assumption) => (
            <p key={assumption}>{assumption}</p>
          ))}
        </div>
      )}

      <AgentStepTimeline steps={detail.steps} />

      {detail.run.expected_outcome && (
        <p className="agent-expected">
          Expected outcome: {detail.run.expected_outcome}
        </p>
      )}
    </section>
  );
}
