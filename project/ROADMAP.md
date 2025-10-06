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
  - Evaluation shortlist: Qwen/QwQ-32B, Qwen3-Math, or other reasoning-tuned models.
  - Benchmark results on curated reasoning/math tasks relevant to NovaOps (financial modeling, research synthesis, long-chain planning).
  - Optional integration as “Reasoner” tool-call target; invoked via router when reasoning depth or math confidence thresholds hit.
- **Tasks**:
  1. Prepare evaluation dataset (internal tasks, open benchmarks, Nova transcripts).
  2. Run comparative inference; capture latency, accuracy, hallucination rates.
  3. Decide single model or ensemble; provision endpoint.
  4. Extend router rules: detect reasoning-heavy prompts (keywords, chain length, user tag) and invoke reasoner model.
  5. Validate: multi-step planning tasks, math stress tests, compliance review with Ops.
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
- **Dependencies**: Milestones 2.1 & 2.2, policy requirements from stakeholders, monitoring stack.

## Phase 3 — Domain Toolkits (Tentative)
*Placeholder for Finance, Data Science, Infra kits once Model Fleet is stable.*

## Phase 4 — Observability & Governance Enhancements (Tentative)
*Signed transcripts, RBAC, policy engine, SIEM integration.*

