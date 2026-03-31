from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional


@dataclass
class AgentResult:
    agent_name: str
    raw_text: str
    parsed: Dict[str, Any]
    success: bool
    confidence_signal: float
    failure_reason: Optional[str] = None


@dataclass
class BreakerDecision:
    allow: bool
    state_before: str
    state_after: str
    tripped: bool
    reason: Optional[str] = None


@dataclass
class RunRecord:
    run_id: str
    task_id: str
    provider: str
    model: str
    cb_type: str
    injection: str
    inject_rate: float
    injection_applied: bool
    upstream_failure: bool
    cascade: bool
    final_success: bool
    breaker_trip_count: int
    planner: Dict[str, Any] = field(default_factory=dict)
    executor: Dict[str, Any] = field(default_factory=dict)
    verifier: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
