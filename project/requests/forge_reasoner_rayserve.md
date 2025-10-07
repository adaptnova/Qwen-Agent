# Forge Launch Request — Ray Serve Thinking Fleet

- **Request ID**: NOVA-P2-REASONER-001
- **Date**: 2025-10-07
- **Owner**: Chase (NovaOps)
- **Assignee**: Forge (PlatformOps)

## Objective
Provision a Ray Serve deployment on the H200 cluster capable of hosting multiple “thinking” LLM specialists (Nova generalist + Qwen/Qwen3-30B-A3B-Thinking-2507 candidate) with fast routing between replicas for NovaOps benchmarking.

## Deliverables
1. Ray Serve app exposing `/nova-reasoner` with routing tags for `generalist` and `thinker`.
2. vLLM workers (or Ray Serve deployments) preloading:
   - `Qwen/Qwen3-VL-30B-A3B-Thinking-FP8` (generalist baseline).
   - `Qwen/Qwen3-30B-A3B-Thinking-2507` (candidate reasoning specialist).
3. API credentials and endpoint URL shared with NovaOps.

## Deployment Guidance
- Target hardware: 1×H200 (80 GB) with CUDA 12.2, Python 3.10, `ray[default]==2.34+`.
- Suggested directory: `/data/rayserve/nova`.
- Install dependencies:
  ```bash
  pip install ray[default]==2.34.0 vllm>=0.5.0.post2
  ```
- Use Ray Serve “multi-deployment” pattern with each model running as a replica:
  ```python
  from ray import serve
  from vllm import AsyncLLMEngine

  @serve.deployment(num_replicas=1, ray_actor_options={"num_gpus": 1})
  class NovaGeneralist:
      def __init__(self):
          self.engine = AsyncLLMEngine(model="Qwen/Qwen3-VL-30B-A3B-Thinking-FP8", trust_remote_code=True)
      async def __call__(self, request): ...

  @serve.deployment(num_replicas=1, ray_actor_options={"num_gpus": 1})
  class NovaThinker:
      def __init__(self):
          self.engine = AsyncLLMEngine(model="Qwen/Qwen3-30B-A3B-Thinking-2507", trust_remote_code=True)
      async def __call__(self, request): ...
  ```
- Expose a router deployment that inspects a `X-Nova-Model` header (values `generalist` or `thinker`) and forwards accordingly.
- Ensure each replica launches with:
  ```
  --enable-auto-tool-choice
  --tool-call-parser hermes
  --reasoning-parser qwen3
  ```
  when using vLLM’s HTTP server mode; if integrating directly in Python, enable matching generate options.

## Validation
1. Warm up both replicas with a simple prompt (`"Summarize latest NovaOps decisions"`).
2. Provide Ray Serve health output (`serve status`) showing both deployments running.
3. Curl tests:
   ```bash
   curl -H "X-Nova-Model: generalist" http://<ray-host>:8001/nova-reasoner -d '{"messages":[...]}'
   curl -H "X-Nova-Model: thinker" http://<ray-host>:8001/nova-reasoner -d '{"messages":[...]}'
   ```
4. Share latency statistics from Ray dashboard or logs so NovaOps can compare load times.

## Dependencies / Risks
- Each model requires ~38 GB VRAM; confirm `num_gpus=1` replica scheduling fits (otherwise stagger tests).
- Fast swap depends on preloading weights; avoid repeated tear-down/start cycles.
- Maintain the existing vLLM endpoints (Nova + coder) during testing; Ray Serve addition must not disrupt production traffic.

## Completion Criteria
- Ray Serve endpoint reachable with both specialists responding.
- Report delivered to NovaOps with endpoint URL, authentication (if any), latency first-response numbers, and any constraints.

## Follow-Up Actions
- Coordinate with NovaOps once endpoint is live so MLflow-backed benchmarks (`scripts/nova_reasoner_benchmark.py --mlflow ...`) can start immediately.
- Provide instructions for scaling replicas or adding additional thinking models if the initial evaluation warrants expansion.
- Keep Ray dashboard accessible to NovaOps during the evaluation window for latency/health monitoring.

## Contact
- Chase (NovaOps): chase@novaops.internal
- Atlas (NovaOps): atlas@novaops.internal
