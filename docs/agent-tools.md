# Agent Tools

Agent tools are backend functions with a fixed name, typed input, permission,
risk, timeout, retry policy, idempotence flag, and allowed agent types. The
registry is the complete capability boundary. It also supplies the safe step
description shown in plans and approval queues; free-form planner descriptions
are not persisted.

## Read-Only Registry

| Tool | Main permission | Agent types |
| --- | --- | --- |
| `weather.read` | `weather.read` | planning, calendar |
| `calendar.read_today` | `calendar.read_private` | planning, calendar |
| `calendar.read_upcoming` | `calendar.read_private` | planning, calendar |
| `memory.search_own` | `memory.read_private` | planning, memory |
| `memory.summary_own` | `memory.read_private` | planning, memory |
| `shared_context.read_allowed` | `shared_context.read` | planning, memory, research |
| `profile.read_self` | `profile.read_self` | all current types |
| `proactive.read_summary` | `context.read_private` | planning, calendar |
| `smart_home.read_entities` | `smart_home.read` | smart home |
| `smart_home.read_sensors` | `smart_home.read` | smart home |
| `system.read_safe_status` | `system.status.read` | planning, research |
| `research.organize_input` | `assistant.use` | research, planning |

Every read also requires `agents.execute_read_only`.

`research.organize_input` operates only on text supplied as the run goal. Its
validated step argument is the fixed value `{"source":"run_goal"}`, so the
full text is not duplicated in step storage. It does not contact websites or
claim current external research.

## Side-Effect Registry

| Tool | Main permission | Additional guard |
| --- | --- | --- |
| `memory.create_own` | `memory.write_private` | separate approval, secret-term rejection |
| `shared_context.create_private` | `shared_context.manage` | private visibility, separate approval |
| `smart_home.turn_on_approved_light` | `smart_home.control_low_risk` | light/switch ID, separate approval |
| `smart_home.turn_off_approved_light` | `smart_home.control_low_risk` | light/switch ID, separate approval |
| `smart_home.activate_approved_scene` | `smart_home.control_low_risk` | scene ID, separate approval |

Every side effect also requires `agents.execute_low_risk`. These tools have no
automatic retries. Smart-home calls still pass through
`ensure_control_allowed`; a model cannot construct a raw Home Assistant domain
or service call.

## Adding A Tool

A future tool must:

1. use a narrow Pydantic input model that forbids unknown fields;
2. return `AgentToolExecutionOutput`;
3. identify its existing Mirrage permission;
4. define side effects and approval policy honestly;
5. call an existing safe service boundary;
6. set a practical timeout and retry rule;
7. add plan-validation, execution, permission, privacy, and failure tests;
8. update this document.

Do not add generic adapters such as `http.request`, `filesystem.open`, or
`home_assistant.call_service`.
