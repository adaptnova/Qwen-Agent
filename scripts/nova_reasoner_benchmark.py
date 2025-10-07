#!/usr/bin/env python3
"""Benchmark Nova thinking models and log structured results."""

from __future__ import annotations

import argparse
import json
import pathlib
import time
import uuid
from dataclasses import dataclass, asdict
from typing import Any, Dict, List

import requests

DEFAULT_TASKS: List[Dict[str, Any]] = [
    {
        "id": "ops_runbook",
        "prompt": "Outline a step-by-step remediation plan for a production web service stuck at 95% CPU. "
                  "Assume Nova can run shell commands and query logs. Provide specific checks and commands.",
        "max_tokens": 600,
    },
    {
        "id": "repo_trace",
        "prompt": "Given a Python repository where tests intermittently fail, describe how you would isolate the flaky test, "
                  "collect evidence, and propose a fix. Focus on concrete actions and tooling.",
        "max_tokens": 600,
    },
    {
        "id": "analysis_chain",
        "prompt": "A user reports that Nova sometimes repeats instructions without taking action. "
                  "Diagnose potential causes and propose mitigations using Nova's tool stack.",
        "max_tokens": 600,
    },
]


@dataclass
class ModelConfig:
    name: str
    endpoint: str
    api_key: str | None = None
    label: str = ""


@dataclass
class RunResult:
    run_id: str
    task_id: str
    model_label: str
    model_name: str
    endpoint: str
    latency_s: float
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    finish_reason: str | None
    output_text: str


def call_model(cfg: ModelConfig, prompt: str, max_tokens: int) -> RunResult:
    """Execute a single chat completion request and capture metrics."""
    url = cfg.endpoint.rstrip("/") + "/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    if cfg.api_key:
        headers["Authorization"] = f"Bearer {cfg.api_key}"
    payload = {
        "model": cfg.name,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.4,
        "top_p": 0.8,
    }
    started = time.monotonic()
    resp = requests.post(url, headers=headers, json=payload, timeout=600)
    latency = time.monotonic() - started
    resp.raise_for_status()
    data = resp.json()
    choice = data["choices"][0]
    usage = data.get("usage", {})
    return RunResult(
        run_id=str(uuid.uuid4()),
        task_id="",
        model_label=cfg.label,
        model_name=cfg.name,
        endpoint=cfg.endpoint,
        latency_s=latency,
        prompt_tokens=usage.get("prompt_tokens"),
        completion_tokens=usage.get("completion_tokens"),
        total_tokens=usage.get("total_tokens"),
        finish_reason=choice.get("finish_reason"),
        output_text=choice["message"]["content"],
    )


def load_tasks(path: str | None) -> List[Dict[str, Any]]:
    if not path:
        return DEFAULT_TASKS
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise ValueError("Tasks file must contain a JSON list")
    return data


def ensure_reports_dir() -> pathlib.Path:
    base = pathlib.Path("/data/nova/reports")
    base.mkdir(parents=True, exist_ok=True)
    return base


def main():
    parser = argparse.ArgumentParser(description="Benchmark Nova thinking models.")
    parser.add_argument("--generalist-endpoint", default="http://10.0.1.1:18000")
    parser.add_argument("--generalist-model", default="Qwen/Qwen3-VL-30B-A3B-Thinking-FP8")
    parser.add_argument("--generalist-api-key", default=None)
    parser.add_argument("--thinker-endpoint", required=True)
    parser.add_argument("--thinker-model", default="Qwen/Qwen3-30B-A3B-Thinking-2507")
    parser.add_argument("--thinker-api-key", default=None)
    parser.add_argument("--tasks-json", default=None,
                        help="Optional path to JSON file containing task objects.")
    parser.add_argument("--output", default=None,
                        help="Optional output path; defaults to /data/nova/reports/nova_reasoner_<timestamp>.jsonl")
    args = parser.parse_args()

    tasks = load_tasks(args.tasks_json)
    reports_dir = ensure_reports_dir()
    timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    output_path = pathlib.Path(args.output or reports_dir / f"nova_reasoner_{timestamp}.jsonl")

    generalist = ModelConfig(
        name=args.generalist_model,
        endpoint=args.generalist_endpoint,
        api_key=args.generalist_api_key,
        label="generalist",
    )
    thinker = ModelConfig(
        name=args.thinker_model,
        endpoint=args.thinker_endpoint,
        api_key=args.thinker_api_key,
        label="thinker",
    )

    results: List[RunResult] = []
    for task in tasks:
        task_id = task.get("id") or f"task_{len(results)}"
        prompt = task["prompt"]
        max_tokens = task.get("max_tokens", 512)
        for cfg in (generalist, thinker):
            print(f"[{task_id}] -> {cfg.label} ({cfg.endpoint})")
            try:
                result = call_model(cfg, prompt, max_tokens)
                result.task_id = task_id
            except Exception as exc:  # pylint: disable=broad-except
                print(f"  ERROR: {exc}")
                result = RunResult(
                    run_id=str(uuid.uuid4()),
                    task_id=task_id,
                    model_label=cfg.label,
                    model_name=cfg.name,
                    endpoint=cfg.endpoint,
                    latency_s=-1.0,
                    prompt_tokens=None,
                    completion_tokens=None,
                    total_tokens=None,
                    finish_reason="error",
                    output_text=str(exc),
                )
            results.append(result)
            print(f"  latency={result.latency_s:.2f}s tokens={result.total_tokens} finish={result.finish_reason}")

    with open(output_path, "w", encoding="utf-8") as fh:
        for item in results:
            fh.write(json.dumps(asdict(item)) + "\n")

    print(f"\nSaved {len(results)} results to {output_path}")


if __name__ == "__main__":
    main()

