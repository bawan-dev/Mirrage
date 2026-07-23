import { useCallback, useEffect, useState, type FormEvent } from 'react';

import {
  cancelAgentRun,
  createAgentRun,
  decideAgentApproval,
  getAgentApprovals,
  getAgentEvents,
  getAgentRun,
  getAgentRuns,
  getAgentStatus,
  getAgentTypes,
  pauseAgentRun,
  planAgentRun,
  resumeAgentRun,
  startAgentRun,
} from '../api';
import type {
  AgentApproval,
  AgentEvent,
  AgentRun,
  AgentRunDetail,
  AgentStatus,
  AgentType,
  AgentTypeInfo,
} from '../types';
import { AgentPlanView } from './AgentPlanView';
import { AgentResultView } from './AgentResultView';
import { AgentRunList } from './AgentRunList';
import { ApprovalPanel } from './ApprovalPanel';

interface AgentWorkspaceProps {
  onClose: () => void;
}

const terminalStatuses = new Set([
  'completed',
  'failed',
  'cancelled',
  'expired',
]);

export function AgentWorkspace({ onClose }: AgentWorkspaceProps) {
  const [status, setStatus] = useState<AgentStatus | null>(null);
  const [types, setTypes] = useState<AgentTypeInfo[]>([]);
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [detail, setDetail] = useState<AgentRunDetail | null>(null);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [approvals, setApprovals] = useState<AgentApproval[]>([]);
  const [agentType, setAgentType] = useState<AgentType>('planning');
  const [goal, setGoal] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refreshRun = useCallback(async (runId: string) => {
    const [nextDetail, nextEvents] = await Promise.all([
      getAgentRun(runId),
      getAgentEvents(runId),
    ]);
    setDetail(nextDetail);
    setEvents(nextEvents);
  }, []);

  const refresh = useCallback(async () => {
    setError(null);
    try {
      const [nextStatus, nextTypes, nextRuns] = await Promise.all([
        getAgentStatus(),
        getAgentTypes(),
        getAgentRuns(),
      ]);
      setStatus(nextStatus);
      setTypes(nextTypes);
      setRuns(nextRuns);
      try {
        setApprovals(await getAgentApprovals());
      } catch {
        setApprovals([]);
      }
      const selectedId = detail?.run.public_id ?? nextRuns[0]?.public_id;
      if (selectedId) {
        await refreshRun(selectedId);
      }
    } catch {
      setError(
        'Agent workspace needs an authenticated trusted device and an active human session on mirror devices.',
      );
    }
  }, [detail?.run.public_id, refreshRun]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!goal.trim() || busy) {
      return;
    }
    setBusy(true);
    setError(null);
    setMessage('Creating a bounded plan...');
    try {
      const created = await createAgentRun({
        agent_type: agentType,
        goal: goal.trim(),
      });
      const planned = await planAgentRun(created.run.public_id);
      setDetail(planned);
      setEvents(await getAgentEvents(planned.run.public_id));
      setGoal('');
      setMessage(
        planned.run.status === 'awaiting_approval'
          ? 'Plan ready. A separate approver must review the requested action.'
          : 'Validated plan ready.',
      );
      setRuns(await getAgentRuns());
      try {
        setApprovals(await getAgentApprovals());
      } catch {
        setApprovals([]);
      }
    } catch {
      setError('Mirrage could not create a safe validated plan.');
      setMessage(null);
    } finally {
      setBusy(false);
    }
  }

  async function runAction(
    action: (runId: string) => Promise<AgentRunDetail>,
    optimisticStatus?: AgentRun['status'],
  ) {
    if (!detail || busy) {
      return;
    }
    const runId = detail.run.public_id;
    setBusy(true);
    setError(null);
    if (optimisticStatus) {
      setDetail({
        ...detail,
        run: { ...detail.run, status: optimisticStatus },
      });
    }
    try {
      const next = await action(runId);
      setDetail(next);
      setEvents(await getAgentEvents(runId));
      setRuns(await getAgentRuns());
      setMessage(`Task ${next.run.status.replaceAll('_', ' ')}.`);
    } catch {
      setError('The requested agent transition was not allowed.');
      await refreshRun(runId);
    } finally {
      setBusy(false);
    }
  }

  async function handleApproval(
    approval: AgentApproval,
    decision: 'approve' | 'deny',
  ) {
    setBusy(true);
    setError(null);
    try {
      await decideAgentApproval(
        approval.approval_id,
        decision,
        `Reviewed in the Mirrage Agent workspace: ${decision}.`,
      );
      setApprovals(await getAgentApprovals());
      if (detail?.run.public_id === approval.run_id) {
        await refreshRun(approval.run_id);
      }
      setMessage(`Action ${decision === 'approve' ? 'approved' : 'denied'}.`);
    } catch {
      setError(
        'Approval failed. Requesters cannot approve their own agent actions.',
      );
    } finally {
      setBusy(false);
    }
  }

  async function handlePause() {
    if (!detail) {
      return;
    }
    try {
      const next = await pauseAgentRun(detail.run.public_id);
      setDetail(next);
      setMessage('Task paused.');
    } catch {
      setError('The task could not be paused at this step boundary.');
    }
  }

  const run = detail?.run ?? null;

  return (
    <div className="agent-workspace animate-focus-in">
      <header className="agent-workspace-header">
        <div>
          <p className="agent-section-label">Bounded agents</p>
          <h1>Agent workspace</h1>
          <p>
            Structured plans, registered tools, separate approvals, and a
            complete safe history.
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close agent workspace"
        >
          Close
        </button>
      </header>

      <div className="agent-status-line">
        <span className={status?.enabled ? 'is-ready' : ''}>
          {status?.enabled ? 'Enabled' : 'Disabled'}
        </span>
        <p>{status?.message ?? 'Checking agent runtime...'}</p>
        <button type="button" disabled={busy} onClick={() => void refresh()}>
          Refresh
        </button>
      </div>

      <form className="agent-create-form" onSubmit={handleCreate}>
        <label htmlFor="agent-type">Agent type</label>
        <select
          id="agent-type"
          value={agentType}
          onChange={(event) => setAgentType(event.target.value as AgentType)}
          disabled={busy || !status?.enabled}
        >
          {(types.length > 0
            ? types
            : [{ name: 'planning' as AgentType, description: '' }]
          ).map((type) => (
            <option key={type.name} value={type.name}>
              {type.name.replace('_', ' ')}
            </option>
          ))}
        </select>
        <label htmlFor="agent-goal">Task</label>
        <textarea
          id="agent-goal"
          value={goal}
          onChange={(event) => setGoal(event.target.value)}
          placeholder="Describe one bounded task"
          rows={3}
          maxLength={2000}
          disabled={busy || !status?.enabled}
        />
        <button
          type="submit"
          disabled={busy || !status?.enabled || !goal.trim()}
        >
          Create plan
        </button>
      </form>

      {error && <p className="agent-error-text">{error}</p>}
      {message && <p className="agent-success-text">{message}</p>}

      <div className="agent-workspace-body">
        <AgentRunList
          activeRunId={run?.public_id ?? null}
          onSelect={(runId) => void refreshRun(runId)}
          runs={runs}
        />

        <main className="agent-active-run">
          {detail ? (
            <>
              <AgentPlanView detail={detail} />
              <div className="agent-run-actions">
                {run?.status === 'ready' && (
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void runAction(startAgentRun, 'running')}
                  >
                    Start
                  </button>
                )}
                {run?.status === 'running' && (
                  <button type="button" onClick={() => void handlePause()}>
                    Pause
                  </button>
                )}
                {run?.status === 'paused' && (
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void runAction(resumeAgentRun, 'running')}
                  >
                    Resume
                  </button>
                )}
                {run && !terminalStatuses.has(run.status) && (
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void runAction(cancelAgentRun)}
                  >
                    Cancel
                  </button>
                )}
              </div>
              <AgentResultView events={events} run={detail.run} />
            </>
          ) : (
            <p className="agent-empty-state">
              Create a task to inspect its validated plan and progress.
            </p>
          )}
        </main>
      </div>

      <ApprovalPanel
        approvals={approvals}
        busy={busy}
        onDecision={(approval, decision) =>
          void handleApproval(approval, decision)
        }
      />
    </div>
  );
}
