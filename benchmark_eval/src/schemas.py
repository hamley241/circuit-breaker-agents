from __future__ import annotations

from dataclasses import dataclass
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


@dataclass
class IntermediateHandoff:
    summary: str
    facts: list[str]
    confidence: float


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
    execution_mode: str = 'state_locked'
    pipeline_variant: str = 'three_stage'
    fault_type: str = 'none'
    upstream_corrupted: bool = False
    fault_variant: str = ''
    verifier_input_source: str = ''
    handoff_has_numeric_values: bool = False
    cb_tripped: bool = False
    trip_reason: str = ''
    intermediate_valid: bool = True
    safe_failure: bool = False
    final_correct: bool = False
    trip_count: int = 0
    stages: List[StageTrace] = Field(default_factory=list)
    final_answer: Optional[str] = None
    reference_answer: Optional[str] = None
    grader_reason: Optional[str] = None
    grading_reason: Optional[str] = None
    observed_final_answer_for_grading: Optional[str] = None
