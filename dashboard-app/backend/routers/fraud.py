"""
Fraud Router - Fraud reports and review.
"""

import logging
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException

from models import FraudReviewRequest, ActionResult

router = APIRouter(prefix="/api", tags=["fraud"])
logger = logging.getLogger(__name__)

# Path will be set from main.py
EMERGENT_LEARNING_PATH = None


def set_paths(elf_path: Path):
    """Set the paths for fraud operations."""
    global EMERGENT_LEARNING_PATH
    EMERGENT_LEARNING_PATH = elf_path


def get_fraud_reviewer():
    """Get a FraudReviewer instance."""
    if EMERGENT_LEARNING_PATH is None:
        raise HTTPException(status_code=500, detail="Paths not configured")

    # Import FraudReviewer from the query directory
    sys.path.insert(0, str(EMERGENT_LEARNING_PATH / "query"))
    from fraud_review import FraudReviewer
    return FraudReviewer()


@router.get("/fraud-reports")
async def get_pending_fraud_reports():
    """Get all pending fraud reports for human review."""
    try:
        reviewer = get_fraud_reviewer()
        reports = reviewer.get_pending_reports()
        return reports
    except Exception as e:
        logger.error(f"Error fetching fraud reports: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fraud-reports/{report_id}")
async def get_fraud_report(report_id: int):
    """Get detailed fraud report with all anomaly signals."""
    try:
        reviewer = get_fraud_reviewer()
        report = reviewer.get_report_with_signals(report_id)

        if not report:
            raise HTTPException(status_code=404, detail=f"Fraud report {report_id} not found")

        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching fraud report {report_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fraud-reports/{report_id}/review")
async def review_fraud_report(report_id: int, review: FraudReviewRequest) -> ActionResult:
    """Record human review outcome for a fraud report."""
    try:
        reviewer = get_fraud_reviewer()
        result = reviewer.record_review_outcome(
            fraud_report_id=report_id,
            outcome=review.outcome,
            reviewed_by=review.reviewed_by,
            notes=review.notes
        )

        outcome_msg = "confirmed as fraud" if review.outcome == "true_positive" else "marked as false positive"

        return ActionResult(
            success=True,
            message=f"Fraud report #{report_id} {outcome_msg}",
            data=result
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error reviewing fraud report {report_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
