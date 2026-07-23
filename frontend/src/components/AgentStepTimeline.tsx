import type { AgentStep } from '../types';

interface AgentStepTimelineProps {
  steps: AgentStep[];
}

export function AgentStepTimeline({ steps }: AgentStepTimelineProps) {
  if (steps.length === 0) {
    return null;
  }

  return (
    <ol className="agent-step-timeline" aria-label="Validated plan steps">
      {steps.map((step) => (
        <li key={step.public_id}>
          <span className="agent-step-number">
            {String(step.step_number).padStart(2, '0')}
          </span>
          <div>
            <strong>{step.description}</strong>
            <p>
              {step.status.replaceAll('_', ' ')}
              {step.approval_required
                ? ` / approval ${step.approval_status ?? 'pending'}`
                : ''}
            </p>
            {step.output_summary && <small>{step.output_summary}</small>}
            {step.error_summary && (
              <small className="agent-error-text">{step.error_summary}</small>
            )}
          </div>
        </li>
      ))}
    </ol>
  );
}
