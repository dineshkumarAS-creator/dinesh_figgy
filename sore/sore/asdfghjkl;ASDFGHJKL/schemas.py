from __future__ import annotations
from datetime import datetime, timezone
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class WeatherPayload(BaseModel):
    rainfall_mm_per_hr: float = Field(..., ge=0.0)
    temperature_c: float
    wind_speed_kmh: float = Field(..., ge=0.0)
    visibility_m: int = Field(..., ge=0)
    weather_condition_code: int
    timestamp_utc: datetime
    city: str
    lat: float
    lon: float
    is_trigger_condition: bool

    model_config = {
        "json_schema_extra": {
            "example": {
                "rainfall_mm_per_hr": 48.5,
                "temperature_c": 26.7,
                "wind_speed_kmh": 18.4,
                "visibility_m": 5000,
                "weather_condition_code": 501,
                "timestamp_utc": "2026-04-13T08:05:00Z",
                "city": "Bengaluru",
                "lat": 12.9716,
                "lon": 77.5946,
                "is_trigger_condition": True,
            }
        }
    }

    @field_validator("timestamp_utc", mode="before")
    def parse_timestamp(cls, value: Optional[str] | datetime) -> datetime:
        if isinstance(value, datetime):
            return value.astimezone(timezone.utc)
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc)


class AQIPayload(BaseModel):
    aqi_index_current: float = Field(..., ge=0.0)
    aqi_index_standardized: int = Field(..., ge=0, le=500)
    pm25: float = Field(..., ge=0.0)
    pm10: float = Field(..., ge=0.0)
    no2: float = Field(..., ge=0.0)
    station_id: str
    city: str
    lat: float
    lon: float
    timestamp_utc: datetime
    is_trigger_condition: bool

    model_config = {
        "json_schema_extra": {
            "example": {
                "aqi_index_current": 320,
                "aqi_index_standardized": 320,
                "pm25": 148.0,
                "pm10": 280.0,
                "no2": 98.0,
                "station_id": "CPCB-DELHI-01",
                "city": "Delhi",
                "lat": 28.7041,
                "lon": 77.1025,
                "timestamp_utc": "2026-04-13T08:10:00Z",
                "is_trigger_condition": False,
            }
        }
    }

    @field_validator("timestamp_utc", mode="before")
    def parse_timestamp(cls, value: Optional[str] | datetime) -> datetime:
        if isinstance(value, datetime):
            return value.astimezone(timezone.utc)
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc)


class EventBase(BaseModel):
    event_type: Literal["curfew", "strike", "protest", "bandh", "other"]
    affected_city: str | None = None
    affected_zones: list[str] = Field(default_factory=list)
    city_extracted: str | None = None
    severity: int = Field(..., ge=1, le=5)
    start_time: datetime
    end_time: datetime | None = None
    source_url: str
    raw_title: str
    source: str
    relevance_score: float | None = None
    timestamp_utc: datetime
    is_trigger_condition: bool


class CurfewEvent(EventBase):
    event_type: Literal["curfew"] = "curfew"


class StrikeEvent(EventBase):
    event_type: Literal["strike"] = "strike"


class BandhEvent(EventBase):
    event_type: Literal["bandh"] = "bandh"


class ProtestEvent(EventBase):
    event_type: Literal["protest"] = "protest"


class OtherEvent(EventBase):
    event_type: Literal["other"] = "other"


EventPayload = Annotated[
    CurfewEvent | StrikeEvent | BandhEvent | ProtestEvent | OtherEvent,
    Field(discriminator="event_type"),
]


# ==============================================================================
# Enriched Event Schemas (for downstream processing)
# ==============================================================================


class EventEnrichment(BaseModel):
    """Enrichment metadata for events."""
    
    enriched_at: datetime
    enricher_service: str
    enrichment_version: str = "1.0"
    
    # Additional context
    affected_workers_estimated: int | None = None
    estimated_impact_hours: float | None = None
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    
    # Metadata tags
    tags: list[str] = Field(default_factory=list)
    remarks: str | None = None


class EnrichedEvent(BaseModel):
    """Event with enrichment data."""
    
    event_id: str  # UUID
    event_payload: EventPayload
    enrichment: EventEnrichment | None = None
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "event_id": "evt_abc123xyz",
                "event_payload": {
                    "event_type": "curfew",
                    "affected_city": "Delhi",
                    "affected_zones": ["DL-01", "DL-02"],
                    "city_extracted": "Delhi",
                    "severity": 4,
                    "start_time": "2026-04-14T08:00:00Z",
                    "end_time": "2026-04-14T20:00:00Z",
                    "source_url": "https://pib.gov.in/press",
                    "raw_title": "Curfew imposed in Delhi",
                    "source": "pib",
                    "relevance_score": 0.95,
                    "timestamp_utc": "2026-04-14T07:55:00Z",
                    "is_trigger_condition": True,
                },
                "enrichment": {
                    "enriched_at": "2026-04-14T08:00:30Z",
                    "enricher_service": "event_enricher",
                    "confidence_score": 0.92,
                    "affected_workers_estimated": 1500,
                    "estimated_impact_hours": 12.0,
                    "tags": ["major_city", "high_severity", "auto_enriched"],
                },
            }
        }
    }


# ==============================================================================
# Batch Event Schemas
# ==============================================================================


class EventBatch(BaseModel):
    """Batch of events for bulk processing."""
    
    batch_id: str
    events: list[EventPayload] = Field(..., min_length=1, max_length=1000)
    batch_source: str  # "govt_feed", "news", etc.
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "batch_id": "batch_2026041414003001",
                "events": [
                    {
                        "event_type": "curfew",
                        "affected_city": "Delhi",
                        "affected_zones": [],
                        "severity": 4,
                        "start_time": "2026-04-14T08:00:00Z",
                        "source_url": "https://pib.gov.in",
                        "raw_title": "Curfew in Delhi",
                        "source": "pib",
                        "timestamp_utc": "2026-04-14T07:55:00Z",
                        "is_trigger_condition": True,
                    }
                ],
                "batch_source": "govt_feed",
                "created_at": "2026-04-14T08:00:00Z",
            }
        }
    }


# ==============================================================================
# Event Routing Schemas
# ==============================================================================


class EventRoutingDecision(BaseModel):
    """Decision for routing an event to downstream services."""
    
    event_id: str
    should_trigger_claim: bool
    affected_worker_ids: list[str] = Field(default_factory=list)
    routing_scores: dict[str, float]  # service_name -> relevance_score
    primary_destination: str  # Which service gets it first
    timestamp_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EventAcknowledgment(BaseModel):
    """Acknowledgment that an event was processed."""
    
    event_id: str
    service_name: str
    status: Literal["received", "processing", "processed", "failed"]
    processed_at: datetime
    error_message: str | None = None
    records_affected: int | None = None


# ==============================================================================
# Dead Letter Queue (DLQ) Schemas
# ==============================================================================


class DLQEvent(BaseModel):
    """Event that failed processing and needs retry/investigation."""
    
    original_event: dict  # Raw event that failed
    failure_reason: str
    failed_service: str
    failure_timestamp_utc: datetime
    retry_count: int = 0
    max_retries: int = 3
    next_retry_at: datetime | None = None
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "original_event": {
                    "event_type": "curfew",
                    "raw_title": "Curfew in Delhi",
                },
                "failure_reason": "Invalid city coordinates",
                "failed_service": "govt_feed_connector",
                "failure_timestamp_utc": "2026-04-14T08:00:15Z",
                "retry_count": 1,
                "max_retries": 3,
                "next_retry_at": "2026-04-14T08:05:15Z",
            }
        }
    }


# ==============================================================================
# Soft Verification Schemas (Layer 5 - Challenge-Response)
# ==============================================================================


class VerificationChallenge(BaseModel):
    """Challenge issued to worker for soft verification."""
    
    challenge_id: str  # UUID
    claim_id: str
    worker_id: str
    challenge_type: Literal["location_ping", "delivery_attempt_confirm", "photo_proof"]
    
    # Timing
    issued_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime  # issued_at + 30 minutes
    
    # Location expectations
    expected_zone_id: str
    expected_lat_range: tuple[float, float]  # (min_lat, max_lat)
    expected_lon_range: tuple[float, float]  # (min_lon, max_lon)
    location_tolerance_km: float = 2.0  # Default 2km radius
    
    # State
    status: Literal["pending", "responded", "expired", "passed", "failed"]
    response_data: dict | None = None
    evaluated_at: datetime | None = None
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "challenge_id": "chall_abc123xyz",
                "claim_id": "claim_def456uvw",
                "worker_id": "worker_123",
                "challenge_type": "location_ping",
                "issued_at": "2026-04-14T12:00:00Z",
                "expires_at": "2026-04-14T12:30:00Z",
                "expected_zone_id": "DL-CENTRAL-01",
                "expected_lat_range": [28.60, 28.65],
                "expected_lon_range": [77.20, 77.25],
                "location_tolerance_km": 2.0,
                "status": "pending",
            }
        }
    }


class WorkerResponse(BaseModel):
    """Worker's response to verification challenge."""
    
    challenge_id: str
    worker_id: str
    response_lat: float
    response_lon: float
    response_timestamp: datetime
    app_foreground: bool  # Was FIGGY app in foreground?
    additional_proof: str | None = None  # Base64-encoded image data


class ChallengeResult(BaseModel):
    """Evaluation result of challenge response."""
    
    passed: bool
    distance_km: float
    timing_score: float = Field(..., ge=0.0, le=1.0)
    failure_reason: str | None = None
    borderline: bool = False
    recommendation: Literal["approve", "manual_review", "reject"]
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "passed": True,
                "distance_km": 1.2,
                "timing_score": 0.9,
                "failure_reason": None,
                "borderline": False,
                "recommendation": "approve",
            }
        }
    }


class SoftVerifyResult(BaseModel):
    """Result of soft verification published to Kafka."""
    
    claim_id: str
    worker_id: str
    challenge_id: str
    passed: bool
    recommendation: Literal["approve", "manual_review", "reject"]
    
    distance_km: float
    timing_score: float
    
    responded_at: datetime | None
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "claim_id": "claim_def456uvw",
                "worker_id": "worker_123",
                "challenge_id": "chall_abc123xyz",
                "passed": True,
                "recommendation": "approve",
                "distance_km": 1.5,
                "timing_score": 0.85,
                "responded_at": "2026-04-14T12:15:30Z",
                "evaluated_at": "2026-04-14T12:15:35Z",
            }
        }
    }



# ==============================================================================
# ML Model Inference Schemas (Layer 4 Orchestrator)
# ==============================================================================


class LSTMScore(BaseModel):
    """Score output from LSTM model (POW confidence)."""
    
    worker_id: str
    minute_bucket: int
    pow_confidence: float = Field(..., ge=-1.0, le=1.0)  # -1.0 = timeout/sentinel
    top_suspicious_timesteps: list[dict] = Field(default_factory=list)  # [{"minute": 5, "score": 0.8}, ...]
    model_version: str
    inference_latency_ms: float
    inferred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class IsolationForestScore(BaseModel):
    """Anomaly score from Isolation Forest (fraud detection)."""
    
    worker_id: str
    minute_bucket: int
    fraud_risk_score: float = Field(..., ge=-1.0, le=1.0)  # -1.0 = timeout/sentinel
    is_anomaly: bool  # True if anomaly detected
    top_anomalous_features: list[dict] = Field(default_factory=list)  # [{"feature": "gps_displacement_m", "value": 500.0, "anomaly_score": 0.9}, ...]
    model_version: str
    inference_latency_ms: float
    inferred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GBMScore(BaseModel):
    """Fraud probability from Gradient Boosting Model."""
    
    worker_id: str
    minute_bucket: int
    fraud_probability: float = Field(..., ge=-1.0, le=1.0)  # -1.0 = timeout/sentinel
    is_fraud_predicted: bool  # True if predicted fraud (>0.5 threshold)
    top_fraud_signals: list[dict] = Field(default_factory=list)  # [{"signal": "income_loss_ratio", "importance": 0.25}, ...]
    model_version: str
    inference_latency_ms: float
    inferred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ParametricTriggerResult(BaseModel):
    """Result from parametric trigger (disruption check)."""
    
    worker_id: str
    minute_bucket: int
    triggered: bool  # True if disruption event detected
    severity_score: float = Field(..., ge=0.0, le=1.0)  # 0-1 normalized
    trigger_types_active: list[str] = Field(default_factory=list)  # ["curfew", "strike", ...]
    event_count: int = 0
    trigger_timestamp: datetime


class MLScoresMessage(BaseModel):
    """Single message consumed from 'ml_scores' Kafka topic."""
    
    model_type: Literal["lstm", "isolation_forest", "gbm", "parametric_trigger"]
    worker_id: str
    minute_bucket: int
    
    # One of these will be populated
    lstm_score: LSTMScore | None = None
    if_score: IsolationForestScore | None = None
    gbm_score: GBMScore | None = None
    trigger_result: ParametricTriggerResult | None = None
    
    # Feature vector for fallback heuristics
    feature_vector: dict | None = None


class CompositeClaimScore(BaseModel):
    """Fused score from all ML models and parametric trigger."""
    
    worker_id: str
    minute_bucket: int
    
    # Core composite score
    composite_claim_score: float = Field(..., ge=0.0, le=1.0)
    disruption_score: float = Field(..., ge=0.0, le=1.0)
    pow_confidence: float = Field(..., ge=0.0, le=1.0)
    fraud_probability: float = Field(..., ge=0.0, le=1.0)
    fraud_risk_score_if: float = Field(..., ge=0.0, le=1.0)  # Backup fraud score
    
    # Anti-spoofing flag
    anti_spoofing_flag: bool = False
    
    #Confidence assessment
    confidence_level: Literal["high", "medium", "low", "insufficient"]
    
    # Explainability
    score_components: dict = Field(default_factory=dict)  # Intermediate values for audit
    top_risk_signals: list[dict] = Field(default_factory=list)  # Merged signals from all models
    
    # Metadata
    trigger_types_active: list[str] = Field(default_factory=list)
    model_versions: dict[str, str] = Field(default_factory=dict)  # model_type -> version
    
    # Performance metrics
    fusion_latency_ms: float = 0.0
    fused_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "worker_id": "worker_123",
                "minute_bucket": 1713081000,
                "composite_claim_score": 0.78,
                "disruption_score": 0.9,
                "pow_confidence": 0.92,
                "fraud_probability": 0.15,
                "fraud_risk_score_if": 0.12,
                "anti_spoofing_flag": False,
                "confidence_level": "high",
                "trigger_types_active": ["curfew"],
                "model_versions": {
                    "lstm": "v2.1.0",
                    "isolation_forest": "v1.5.0",
                    "gbm": "v3.0.1",
                },
                "fusion_latency_ms": 12.5,
            }
        }
    }


class RoutingDecision(BaseModel):
    """Route claim to Layer 5 for payout processing."""
    
    worker_id: str
    minute_bucket: int
    
    # Routing decision
    route: Literal["auto_payout", "soft_verify", "manual_flag"]
    routing_reason: str
    
    # Supporting info
    composite_claim_score: float
    confidence_level: Literal["high", "medium", "low", "insufficient"]
    
    # Additional checks
    requires_live_check: bool = False
    
    # Metadata
    routing_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "worker_id": "worker_123",
                "minute_bucket": 1713081000,
                "route": "auto_payout",
                "routing_reason": "high_confidence_genuine",
                "composite_claim_score": 0.78,
                "confidence_level": "high",
                "requires_live_check": False,
            }
        }
    }

