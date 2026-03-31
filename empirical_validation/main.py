from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from clients.mock_client import MockLLMClient
from clients.openai_client import OpenAILLMClient
from config import SETTINGS
from evaluation.metrics import summarize_jsonl
from runner import run_experiment


def build_client(provider: str):
    if provider == "mock":
        return MockLLMClient(), "mock-model"
    if provider == "openai":
        if not SETTINGS.openai_api_key:
            raise ValueError("OPENAI_API_KEY is missing. Put it in .env or environment.")
        return OpenAILLMClient(SETTINGS.openai_api_key, SETTINGS.openai_model), SETTINGS.openai_model
    raise ValueError(f"Unknown provider: {provider}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=["mock", "openai"], default="mock")
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--cb-type", choices=["no_cb", "ai_cb", "adaptive_cb"], default="no_cb")
    parser.add_argument(
        "--injection",
        choices=["none", "corrupt_json", "contradictory_fact", "context_overload", "empty_tool_result"],
        default="none",
    )
    parser.add_argument("--inject-rate", type=float, default=0.0)
    parser.add_argument("--dataset", type=Path, default=Path("tasks/sample_tasks.jsonl"))
    args = parser.parse_args()

    client, model = build_client(args.provider)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    jsonl_path = SETTINGS.outputs_dir / f"raw_runs_{timestamp}.jsonl"
    csv_path = SETTINGS.outputs_dir / f"summary_{timestamp}.csv"

    run_experiment(
        client=client,
        provider=args.provider,
        model=model,
        dataset_path=args.dataset,
        runs=args.runs,
        cb_type=args.cb_type,
        injection_name=args.injection,
        inject_rate=args.inject_rate,
        output_jsonl=jsonl_path,
    )

    summary = summarize_jsonl(jsonl_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(csv_path, index=False)
    print(f"Wrote raw runs to: {jsonl_path}")
    print(f"Wrote summary to: {csv_path}")
    print(summary)


if __name__ == "__main__":
    main()
