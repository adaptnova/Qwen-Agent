# Phase 2.1 – Qwen3-Coder Integration Spec

## Goal
Augment Nova with a Qwen3-Coder specialist and routing logic that detects code-heavy tasks and forwards them to the coder model while keeping the existing tool suite intact.

## Scope
- Provision/configure vLLM endpoint for Qwen3-Coder (placeholder URL until serving team finalizes).
- Implement router agent combining Nova (generalist) + Coder specialist using existing Qwen-Agent router.
- Define detection heuristics (prompt keywords, tool usage hints, user directives) to decide when to call the Coder model.
- Ensure transcripts/logs capture which model handled each turn.
- Provide smoke tests and documentation.

## Deliverables
1. **Config/Script** `examples/nova_router.py` instantiating:
   - Generalist agent (existing Nova config).
   - Coder agent (Qwen3-Coder model, code-focused tool subset).
   - Router agent for automatic switching.
2. **Documentation** updates in `project/ROADMAP.md` and `project/DEPLOYMENT.md` describing multi-model setup.
3. **Health/validation** instructions for verifying coder routing.

## Milestones & Tasks

### M2.1-A — Infrastructure Readiness
- [ ] Coordinate with serving team for Qwen3-Coder vLLM endpoint (e.g., `http://<host>:<port>/v1`).
- [ ] Add config placeholders (`NOVA_CODER_LLM_SERVER`, `NOVA_CODER_LLM_MODEL`).
- [ ] Update requirements if additional packages are needed (none expected).

### M2.1-B — Router Implementation
- [x] Create spec (this document).
- [ ] Implement `examples/nova_router.py` showcasing router usage.
- [ ] Expose config via env variables & optional YAML.
- [ ] Add detection heuristics (keywords like “code”, “python”, file diff) and fallback to generalist.
- [ ] Tag transcript events with `model=generalist/coder` for audit.

### M2.1-C — Testing & Docs
- [ ] Add instructions/tests: run router demo, ensure coder path hits coder model.
- [ ] Update `project/DEPLOYMENT.md` with multi-model section.
- [ ] Add roadmap status once completed.

## Open Questions
- Final coder endpoint & authentication? (TBD by infra.)
- Do we need strict policy gating (e.g., only allow coder to run `system_shell` in code workspaces)? Possibly Phase 2.3 policy engine.
- Should reasoning model integration follow same router pattern (likely yes; consistent architecture).

