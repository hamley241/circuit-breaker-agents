from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TaskRecord(BaseModel):
    task_id: str
    question: str
    reference_answer: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CheckerResult(BaseModel):
    valid: bool
    confidence: float
    reasons: List[str] = Field(default_factory=list)


class StageTrace(BaseModel):
    stage: str
    raw_output: Any
    checker: CheckerResult
    breaker_tripped: bool = False
    used_fallback: bool = False


class RunTrace(BaseModel):
    task_id: str
    policy: str
    upstream_failure_seen: bool = False
    final_success: bool = False
    cascade: bool = False
    trip_count: int = 0
    stages: List[StageTrace] = Field(default_factory=list)
    final_answer: Optional[str] = None
    grader_reason: Optional[str] = None
