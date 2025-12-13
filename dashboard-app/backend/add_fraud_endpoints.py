#!/usr/bin/env python3
"""
Integration script to add fraud review endpoints to main.py

Run this to add fraud review API endpoints to the dashboard backend.
"""

from pathlib import Path

MAIN_PY = Path(__file__).parent / "main.py"

# Code to add after session_index import
IMPORT_CODE = """
# Import fraud review module
sys.path.insert(0, str(EMERGENT_LEARNING_PATH / "query"))
from fraud_review import FraudReviewer
"""

# Pydantic model to add after SpikeReportRate
MODEL_CODE = """

class FraudReviewRequest(BaseModel):
    outcome: str  # 'true_positive' or 'false_positive'
    reviewed_by: Optional[str] = 'human'
    notes: Optional[str] = None
"""

# API endpoints to add before workflow management section
ENDPOINTS_CODE = """

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


def main():
    print("Adding fraud review endpoints to main.py...")

    # Read current content
    content = MAIN_PY.read_text()

    # Check if already added
    if "FraudReviewer" in content:
        print("[OK] Fraud review endpoints already added!")
        return

    # Add import after session_index import
    content = content.replace(
        "from session_index import SessionIndex",
        "from session_index import SessionIndex" + IMPORT_CODE
    )

    # Add Pydantic model after SpikeReportRate
    content = content.replace(
        "class SpikeReportRate(BaseModel):\n    score: float  # 0-5 usefulness score\n\n\nclass ActionResult(BaseModel):",
        "class SpikeReportRate(BaseModel):\n    score: float  # 0-5 usefulness score" + MODEL_CODE + "\n\nclass ActionResult(BaseModel):"
    )

    # Add endpoints before workflow management
    content = content.replace(
        "# ==============================================================================\n# REST API: Workflow Management\n# ==============================================================================",
        ENDPOINTS_CODE + "\n# ==============================================================================\n# REST API: Workflow Management\n# =============================================================================="
    )

    # Write back
    MAIN_PY.write_text(content)

    print("[OK] Successfully added fraud review endpoints!")
    print("\nAdded:")
    print("  - FraudReviewer import")
    print("  - FraudReviewRequest Pydantic model")
    print("  - GET /api/fraud-reports")
    print("  - GET /api/fraud-reports/{report_id}")
    print("  - POST /api/fraud-reports/{report_id}/review")
    print("\nRestart the dashboard backend to use the new endpoints.")


if __name__ == "__main__":
    main()
