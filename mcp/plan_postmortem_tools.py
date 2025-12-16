"""
Plan-Postmortem MCP Tools Extension

Add this to elf_server.py by importing and registering the tools.
"""
import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

# Base path for database
BASE_DIR = Path(__file__).resolve().parent.parent


class RecordPlanInput(BaseModel):
    """Input for elf_record_plan tool."""
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(..., description="Brief task title", min_length=3, max_length=200)
    description: str = Field(default="", description="What we're trying to accomplish", max_length=2000)
    approach: str = Field(default="", description="How we plan to do it", max_length=2000)
    risks: str = Field(default="", description="Identified risks/concerns", max_length=1000)
    expected_outcome: str = Field(default="", description="What success looks like", max_length=1000)
    domain: str = Field(default="", description="Domain category", max_length=100)


class RecordPostmortemInput(BaseModel):
    """Input for elf_record_postmortem tool."""
    model_config = ConfigDict(str_strip_whitespace=True)

    plan_id: Optional[int] = Field(default=None, description="Link to plan ID (recommended)")
    title: str = Field(default="", description="Brief description", max_length=200)
    actual_outcome: str = Field(..., description="What actually happened", min_length=5, max_length=2000)
    divergences: str = Field(default="", description="What differed from plan", max_length=2000)
    went_well: str = Field(default="", description="What succeeded", max_length=1000)
    went_wrong: str = Field(default="", description="What failed", max_length=1000)
    lessons: str = Field(default="", description="Key takeaways", max_length=2000)
    domain: str = Field(default="", description="Domain category", max_length=100)


def generate_task_id(title: str) -> str:
    """Generate a unique task_id slug from title."""
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'\s+', '-', slug)
    slug = slug[:40].strip('-')
    timestamp = datetime.now().strftime('%Y%m%d-%H%M')
    return f"{slug}-{timestamp}"


def get_db_path() -> Path:
    return BASE_DIR / "memory" / "index.db"


async def record_plan_impl(params: RecordPlanInput) -> str:
    """Implementation of elf_record_plan."""
    try:
        db_path = get_db_path()
        task_id = generate_task_id(params.title)

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO plans (task_id, title, description, approach, risks, expected_outcome, domain)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (task_id, params.title, params.description, params.approach, 
              params.risks, params.expected_outcome, params.domain))

        plan_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return json.dumps({
            "success": True,
            "plan_id": plan_id,
            "task_id": task_id,
            "title": params.title,
            "message": f"Plan recorded. Use plan_id={plan_id} when creating postmortem."
        }, indent=2)

    except Exception as e:
        return json.dumps({"success": False, "error": f"{type(e).__name__}: {str(e)}"})


async def record_postmortem_impl(params: RecordPostmortemInput) -> str:
    """Implementation of elf_record_postmortem."""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get plan info if linked
        plan = None
        if params.plan_id:
            cursor.execute("SELECT * FROM plans WHERE id = ?", (params.plan_id,))
            row = cursor.fetchone()
            if row:
                plan = dict(row)
            else:
                conn.close()
                return json.dumps({"success": False, "error": f"Plan ID {params.plan_id} not found"})

        # Determine title
        title = params.title
        if not title and plan:
            title = f"Postmortem: {plan['title']}"
        if not title:
            title = "Untitled Postmortem"

        # Determine domain
        domain = params.domain or (plan.get('domain', '') if plan else '')

        # Insert postmortem
        cursor.execute("""
            INSERT INTO postmortems (plan_id, title, actual_outcome, divergences, went_well, went_wrong, lessons, domain)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (params.plan_id, title, params.actual_outcome, params.divergences,
              params.went_well, params.went_wrong, params.lessons, domain))

        postmortem_id = cursor.lastrowid

        # Mark plan as completed if linked
        if params.plan_id:
            cursor.execute("""
                UPDATE plans SET status = 'completed', completed_at = ? WHERE id = ?
            """, (datetime.now().isoformat(), params.plan_id))

        conn.commit()
        conn.close()

        result = {
            "success": True,
            "postmortem_id": postmortem_id,
            "plan_id": params.plan_id,
            "linked_to_plan": params.plan_id is not None,
            "title": title
        }

        # Add learning analysis if linked to plan
        if plan:
            result["analysis"] = {
                "plan_title": plan["title"],
                "expected_outcome": plan.get("expected_outcome", ""),
                "actual_outcome": params.actual_outcome,
                "had_divergences": bool(params.divergences),
                "lessons_captured": bool(params.lessons)
            }

        return json.dumps(result, indent=2)

    except Exception as e:
        return json.dumps({"success": False, "error": f"{type(e).__name__}: {str(e)}"})
