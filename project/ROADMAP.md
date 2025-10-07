# NovaOps Roadmap

## Phase 2 — Model Fleet Expansion (Immediate Priority)

### Objective
Enable Nova to orchestrate multiple Qwen-family models, routing work to the best specialist (coding, reasoning/math, multimodal) while sharing the existing tool suite and control plane.

### Milestone 2.1 — Qwen3-Coder Integration
- **Target**: 2 weeks after vLLM serving of primary model is live.
- **Deliverables**:
  - Dedicated vLLM service for `Qwen/Qwen3-Coder-…` (exact SKU TBD with serving team).
  - Router agent that detects code-heavy tasks (heuristics + optional explicit user flag) and forwards to Coder model.
  - Shared tool registry; code-specific tool prefs (e.g., prefer `python_executor`, `system_shell` for build/test).
  - Regression tests to ensure routing transparency.
- **Tasks**:
  1. Coordinate with infra to provision Qwen3-Coder endpoint (metrics, scaling).
  2. Extend Nova’s config to describe model pool (primary VL + coder) and routing rules.
  3. Implement router agent (inherit from Qwen-Agent Router) with detection heuristics + override hooks.
  4. Update transcripts/logging to tag which model handled each turn; adjust redaction if needed.
  5. Validation: coding workloads (repo analysis, bug fix patching, test execution) across both models.
- **Dependencies**: vLLM image for Qwen3-Coder, GPU capacity, baseline test suite.

### Milestone 2.2 — Reasoning Specialist (QwQ / Math)
- **Target**: Begin once Milestone 2.1 is in staging; aim for completion +1 week.
- **Deliverables**:
  - Evaluation shortlist: Qwen/QwQ-32B, Qwen3-Math, Qwen/Qwen3-30B-A3B-Thinking-2507, or other reasoning-tuned models.
  - Benchmark results on curated reasoning/math tasks relevant to NovaOps (financial modeling, research synthesis, long-chain planning).
  - Optional integration as “Reasoner” tool-call target; invoked via router when reasoning depth or math confidence thresholds hit.
- **Tasks**:
  1. Prepare evaluation dataset (internal tasks, open benchmarks, Nova transcripts).
  2. Stand up Ray Serve deployment on H200 with replicas for the Nova generalist and candidate thinking models (per `project/requests/forge_reasoner_rayserve.md`).
  3. Run comparative inference using `scripts/nova_reasoner_benchmark.py`; capture latency, accuracy, hallucination rates; store reports under `/data/nova/reports/`.
  4. Decide single model or ensemble; provision endpoint.
  5. Extend router rules: detect reasoning-heavy prompts (keywords, chain length, user tag) and invoke reasoner model.
  6. Validate: multi-step planning tasks, math stress tests, compliance review with Ops.
- **Dependencies**: Access to candidate model weights/endpoints, GPU budget for benchmarking.

### Milestone 2.3 — Multi-Model “Squad” Pattern
- **Target**: Following Milestones 2.1–2.2; timeline 2–3 weeks.
- **Deliverables**:
  - Architecture where Nova (generalist VL) orchestrates specialist agents (Coder, Reasoner, Multimodal) via shared control plane and tool kit.
  - Policy layer for enabling/disabling specialists per domain (NovaOps-core, Finance, Data Science).
  - Monitoring dashboards per agent/model (tool usage, success rates, latency).
- **Tasks**:
  1. Define squad roles + responsibilities; document routing criteria.
  2. Implement coordinator agent that sequences tasks and aggregates responses (possible adoption of Qwen-Agent’s `MultiAgentHub`).
  3. Introduce policy config (YAML/JSON) for kit activation per agent persona.
  4. Extend transcripts to tag interactions by agent/model for audit.
  5. Build dashboard (Grafana/Prometheus or ELK) for per-model metrics; integrate with existing logging.
  6. End-to-end drill: complex scenario requiring coding, reasoning, and multimodal analysis (e.g., “analyze website, scrape data, write ETL script, summarize findings”).
  7. Integrate Threshold MCP suite once available and document activation playbook per domain.
- **Dependencies**: Milestones 2.1 & 2.2, policy requirements from stakeholders, monitoring stack.

## Phase 3 — Domain Toolkits (Finance, Data Science, Infra)

### Milestone 3.1 — Finance Kit
- **Deliverables**:
  - API connectors for market/ledger data (Bloomberg-like, internal APIs).
  - Risk engines integration (VaR, scenario analysis) exposed as tools.
  - Compliance prompt wrappers to enforce audit-friendly language.
- **Tasks**:
  1. Gather data source requirements (APIs, auth, rate limits).
  2. Build & register toolkit (e.g., `finance_market_data`, `finance_risk_calc`).
  3. Create compliance wrapper prompts + policy configs.
  4. Validate with finance ops scenarios.

### Milestone 3.2 — Data Science Kit
- **Deliverables**:
  - Jupyter container orchestration, dataset catalog integration, notebook→artifact publishing.
  - Tools for spark jobs, data validation suites.
- **Tasks**:
  1. Choose container runtime (Docker/systemd-nspawn) and implement management tools.
  2. Integrate dataset metadata service (e.g., Feast, DataHub) for search and access.
  3. Automate notebook export (HTML/PDF/MLflow) and storage in /data/nova artifacts.
  4. Test on DS workflows (EDA, modeling, reporting).

### Milestone 3.3 — Infrastructure Kit
- **Deliverables**:
  - Terraform/Ansible wrappers, cloud CLI integration (AWS/Azure/GCP/On-prem), incident response playbooks.
- **Tasks**:
  1. Wrap IaC commands with guardrails (plan/apply tagging, dry-run defaults).
  2. Integrate with incident tooling (PagerDuty, Slack alerts) for auto-remediation.
  3. Provide guardrail policies (what environments Nova can change).
  4. Validate with staged infra changes and simulated incidents.

## Phase 4 — Observability & Ops Enhancements

### Milestone 4.1 — Streaming Metrics & Dashboards
- **Deliverables**: Prometheus exporters for tool usage, latency, errors; Grafana dashboards.
- **Tasks**: instrument transcripts/control server, push metrics, build dashboards.

### Milestone 4.2 — Enhanced Auditing
- **Deliverables**: Cryptographically signed transcripts, immutable storage (WORM/SIEM integration).
- **Tasks**: sign transcripts, push to secure store, integrate with security team workflows.

### Milestone 4.3 — Adaptive Throttling & Policy Engine
- **Deliverables**: Dynamic concurrency limits based on system load/policies; per-agent tool enable/disable.
- **Tasks**: monitor load, implement policy configs, throttle tool calls when thresholds hit.

### Milestone 4.4 — Hardening & Policy Controls
- **Deliverables**:
  - Policy engine to enable/disable toolkits per persona (NovaOps-core, Finance-Nova, DS-Nova).
  - Role-based secrets injection (per-agent secret scopes).
  - Sandbox modes (“read-only”, “simulation”) for staging.
- **Tasks**:
  1. Design policy schema & enforcement layer (YAML/JSON + runtime checks).
  2. Implement secrets scoping (possibly via templated env files or secret managers).
  3. Add runtime switches for sandbox modes; validate against destructive commands.

### Milestone 4.5 — Automation & Lifecycle
- **Deliverables**:
  - CI/CD pipeline (tests, lint, healthcheck) with deploy gating (Nova-assisted where possible).
  - Auto-scaling/staging scripts for multi-region or multi-environment rollout.
- **Tasks**:
  1. Integrate GitHub Actions (or internal CI) running `scripts/run_tests.sh`, `scripts/nova_healthcheck.py` (mock).
  2. Build deployment scripts (Ansible/Terraform) to spin up Nova stacks.
  3. Load-test & prepare staging configs for future multi-region deployments.

## Phase 5 — UX & Collaboration

### Milestone 5.1 — NovaOps Console
- **Deliverables**: Web UI on FastAPI control for queue, status, logs, kill switch.
- **Tasks**: build React/Next (or similar) front-end, secured auth, integrate transcripts/log views.

### Milestone 5.2 — Slack/Teams Integration
- **Deliverables**: Command/response interface with approvals, notifications.
- **Tasks**: build bot connectors, map commands to control API, add optional human approvals per domain.
