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
    verifier_name: str = ''
    verifier_variant: str = ''
    recoverability_score: Optional[float] = None
    recoverability_missing_fields: List[str] = Field(default_factory=list)
    recoverability_raw_response: Optional[str] = None
    verifier_reasoning: Optional[str] = None
    verifier_used_additional_context: Optional[bool] = None


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
    observed_only: bool = False
    verifier_input_source: str = ''
    stage_spec_used: bool = False
    stage_spec_variant: str = ''


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
    mode: str = 'intervention'
    verifier_name: str = ''
    verifier_variant: str = ''
    stage1_output: Optional[Any] = None
    stage2_handoff: Optional[Any] = None
    predicted_trip: bool = False
    predicted_trip_reason: str = ''
    recoverability_stage1: Optional[float] = None
    recoverability_stage2: Optional[float] = None
    reconstruction_gap: Optional[float] = None
    oracle_stage3_from_stage1_success: Optional[bool] = None
    oracle_stage3_from_stage1_answer: Optional[str] = None
    recoverable_handoff_failure: Optional[bool] = None
    fallback_attempted: bool = False
    fallback_success: Optional[bool] = None
    trip_on_true_cascade: Optional[bool] = None
    trip_on_false_alarm: Optional[bool] = None
