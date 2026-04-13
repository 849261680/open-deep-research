from __future__ import annotations

import os
from dataclasses import dataclass
from dataclasses import field


def estimate_tokens(text: str) -> int:
    """Cheap token estimate for providers that do not return usage metadata."""
    if not text:
        return 0
    return max(1, round(len(text) / 4))


@dataclass
class CostTracker:
    """Tracks estimated LLM token usage and cost for one research task."""

    model: str = "deepseek-chat"
    input_cost_per_1m_tokens: float = field(default_factory=lambda: _env_float(
        "DEEPSEEK_INPUT_COST_PER_1M_TOKENS",
        0.28,
    ))
    output_cost_per_1m_tokens: float = field(default_factory=lambda: _env_float(
        "DEEPSEEK_OUTPUT_COST_PER_1M_TOKENS",
        0.42,
    ))
    calls: list[dict[str, object]] = field(default_factory=list)

    def track_llm_call(self, *, step: str, prompt: str, response: str) -> None:
        input_tokens = estimate_tokens(prompt)
        output_tokens = estimate_tokens(response)
        input_cost = input_tokens * self.input_cost_per_1m_tokens / 1_000_000
        output_cost = output_tokens * self.output_cost_per_1m_tokens / 1_000_000
        self.calls.append(
            {
                "step": step,
                "model": self.model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "estimated_cost_usd": round(input_cost + output_cost, 8),
                "estimated": True,
            }
        )

    def summary(self) -> dict[str, object]:
        input_tokens = sum(int(call["input_tokens"]) for call in self.calls)
        output_tokens = sum(int(call["output_tokens"]) for call in self.calls)
        estimated_cost_usd = sum(
            float(call["estimated_cost_usd"]) for call in self.calls
        )
        return {
            "model": self.model,
            "estimated": True,
            "pricing_source": "defaults_or_env",
            "input_cost_per_1m_tokens": self.input_cost_per_1m_tokens,
            "output_cost_per_1m_tokens": self.output_cost_per_1m_tokens,
            "total_input_tokens": input_tokens,
            "total_output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "estimated_cost_usd": round(estimated_cost_usd, 8),
            "calls": self.calls,
        }


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default
