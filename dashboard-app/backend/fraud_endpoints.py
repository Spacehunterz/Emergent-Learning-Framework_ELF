"""
Fraud Review API Endpoints

Add these endpoints to main.py to enable fraud report review functionality.
"""

from typing import Optional
from pydantic import BaseModel
from pathlib import Path
import sys

# Add fraud_review module to path
EMERGENT_LEARNING_PATH = Path.home() / ".claude" / "emergent-learning"
sys.path.insert(0, str(EMERGENT_LEARNING_PATH / "query"))

from fraud_review import FraudReviewer


class FraudReviewRequest(BaseModel):
    outcome: str  # 'true_positive' or 'false_positive'
    reviewed_by: Optional[str] = 'human'
    notes: Optional[str] = None


# ============================================================================
# Add these endpoints to main.py
# ============================================================================

"""
# ==============================================================================
# REST API: Fraud Review
# ==============================================================================

@app.get("/api/fraud-reports")
async def get_pending_fraud_reports():
    \"\"\"Get all pending fraud reports for human review.\"\"\"
    try:
        reviewer = FraudReviewer()
        reports = reviewer.get_pending_reports()
        return reports
    except Exception as e:
        logger.error(f"Error fetching fraud reports: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/fraud-reports/{report_id}")
async def get_fraud_report(report_id: int):
    \"\"\"Get detailed fraud report with all anomaly signals.\"\"\"
    try:
        reviewer = FraudReviewer()
        report = reviewer.get_report_with_signals(report_id)

        if not report:
            raise HTTPException(status_code=404, detail=f"Fraud report {report_id} not found")

        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching fraud report {report_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/fraud-reports/{report_id}/review")
async def review_fraud_report(report_id: int, review: FraudReviewRequest) -> ActionResult:
    \"\"\"Record human review outcome for a fraud report.\"\"\"
    try:
        reviewer = FraudReviewer()
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
"""

# Instructions for adding to main.py:
# 1. Add import at top:
#    sys.path.insert(0, str(EMERGENT_LEARNING_PATH / "query"))
#    from fraud_review import FraudReviewer
#
# 2. Add FraudReviewRequest model to Pydantic models section
#
# 3. Copy the three @app endpoints above before "# Serve Frontend" section
