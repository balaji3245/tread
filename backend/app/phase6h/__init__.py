"""
Phase 6H: Locked Final OOS Validation Package
"""
from app.phase6h.models import (
    FINAL_OOS_DATE_RANGE,
    FINAL_OOS_END_TS,
    FINAL_OOS_START_TS,
    FinalOOSComparison,
    FinalOOSManifest,
    FinalOOSTradeAudit,
    FinalOOSValidationArtifact,
    FinalOOSVerdict,
    PerformanceSliceMetrics,
)
from app.phase6h.final_oos_engine import (
    FinalOOSValidationEngine,
    compute_slice_metrics,
)

__all__ = [
    "FINAL_OOS_DATE_RANGE",
    "FINAL_OOS_END_TS",
    "FINAL_OOS_START_TS",
    "FinalOOSComparison",
    "FinalOOSManifest",
    "FinalOOSTradeAudit",
    "FinalOOSValidationArtifact",
    "FinalOOSVerdict",
    "PerformanceSliceMetrics",
    "FinalOOSValidationEngine",
    "compute_slice_metrics",
]
