import type { AgentApproval } from '../types';

interface ApprovalPanelProps {
  approvals: AgentApproval[];
  busy: boolean;
  onDecision: (approval: AgentApproval, decision: 'approve' | 'deny') => void;
}

export function ApprovalPanel({
  approvals,
  busy,
  onDecision,
}: ApprovalPanelProps) {
  if (approvals.length === 0) {
    return null;
  }

  return (
    <section className="agent-approval-panel">
      <p className="agent-section-label">Separate approval queue</p>
      {approvals.map((approval) => (
        <div key={approval.approval_id}>
          <span>{approval.agent_type.replace('_', ' ')}</span>
          <strong>{approval.description}</strong>
          <p>{approval.risk_level} risk / expires locally</p>
          <div className="agent-inline-actions">
            <button
              type="button"
              disabled={busy}
              onClick={() => onDecision(approval, 'approve')}
            >
              Approve
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => onDecision(approval, 'deny')}
            >
              Deny
            </button>
          </div>
        </div>
      ))}
    </section>
  );
}
