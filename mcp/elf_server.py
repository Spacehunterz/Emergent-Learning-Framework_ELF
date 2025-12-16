#!/usr/bin/env python3
"""
ELF MCP Server - Emergent Learning Framework exposed via Model Context Protocol.

This server exposes ELF's knowledge and recording capabilities to external tools
like claude-flow, enabling them to:
- Query the building for context (golden rules, heuristics, learnings)
- Record heuristics and failures
- Check pending CEO decisions
- Search knowledge base

Usage:
    python elf_server.py                    # Run with stdio transport (default)
    claude mcp add elf python ~/.claude/emergent-learning/mcp/elf_server.py
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# Add parent directories to path for imports
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
# Only add BASE_DIR, not subdirectories - let Python find packages properly
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# MCP imports
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, field_validator, ConfigDict

# Import QuerySystem (async) - must be after sys.path setup
from query import QuerySystem

# Initialize the MCP server
mcp = FastMCP("ELF_FLOW_MCP")


# ============================================================================
# Pydantic Models for Input Validation
# ============================================================================

class DepthLevel(str, Enum):
    """Context depth levels for querying."""
    MINIMAL = "minimal"
    STANDARD = "standard"
    DEEP = "deep"


class SourceType(str, Enum):
    """Source types for heuristics."""
    FAILURE = "failure"
    SUCCESS = "success"
    OBSERVATION = "observation"


class QueryInput(BaseModel):
    """Input for elf_query tool."""
    model_config = ConfigDict(str_strip_whitespace=True)

    domain: Optional[str] = Field(
        default=None,
        description="Domain to focus on (e.g., 'coordination', 'debugging', 'architecture')",
        max_length=100
    )
    depth: DepthLevel = Field(
        default=DepthLevel.STANDARD,
        description="Context depth: 'minimal' (golden rules only), 'standard' (+ heuristics/learnings), 'deep' (+ experiments, ADRs)"
    )
    max_tokens: int = Field(
        default=5000,
        description="Maximum approximate tokens to return",
        ge=500,
        le=20000
    )


class RecordHeuristicInput(BaseModel):
    """Input for elf_record_heuristic tool."""
    model_config = ConfigDict(str_strip_whitespace=True)

    domain: str = Field(
        ...,
        description="Domain for the heuristic (e.g., 'react', 'testing', 'git')",
        min_length=1,
        max_length=100
    )
    rule: str = Field(
        ...,
        description="The heuristic rule statement (e.g., 'Always validate inputs before processing')",
        min_length=5,
        max_length=500
    )
    explanation: str = Field(
        default="",
        description="Explanation of why this heuristic works",
        max_length=5000
    )
    source: SourceType = Field(
        default=SourceType.OBSERVATION,
        description="How this heuristic was discovered: 'failure', 'success', or 'observation'"
    )
    confidence: float = Field(
        default=0.7,
        description="Confidence level from 0.0 to 1.0",
        ge=0.0,
        le=1.0
    )

    @field_validator('domain')
    @classmethod
    def validate_domain(cls, v: str) -> str:
        """Sanitize domain for use as filename."""
        v = v.lower().replace(' ', '-')
        v = re.sub(r'[^a-z0-9-]', '', v)
        return v.strip('-')


class RecordFailureInput(BaseModel):
    """Input for elf_record_failure tool."""
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(
        ...,
        description="Brief title describing the failure",
        min_length=5,
        max_length=500
    )
    domain: str = Field(
        ...,
        description="Domain where the failure occurred",
        min_length=1,
        max_length=100
    )
    summary: str = Field(
        ...,
        description="Summary of what happened and what was learned",
        min_length=10,
        max_length=50000
    )
    severity: int = Field(
        default=3,
        description="Severity level from 1 (minor) to 5 (critical)",
        ge=1,
        le=5
    )
    tags: Optional[str] = Field(
        default=None,
        description="Comma-separated tags for categorization",
        max_length=500
    )


class SearchInput(BaseModel):
    """Input for elf_search tool."""
    model_config = ConfigDict(str_strip_whitespace=True)

    query: str = Field(
        ...,
        description="Search query to find relevant knowledge",
        min_length=2,
        max_length=500
    )
    domain: Optional[str] = Field(
        default=None,
        description="Optional domain to filter results",
        max_length=100
    )
    limit: int = Field(
        default=10,
        description="Maximum number of results to return",
        ge=1,
        le=50
    )


# ============================================================================
# Helper Functions
# ============================================================================

async def get_query_system():
    """Get or create QuerySystem instance (async)."""
    return await QuerySystem.create(base_path=str(BASE_DIR))


def get_ceo_inbox_files() -> List[Path]:
    """Get list of pending CEO inbox files."""
    inbox_dir = BASE_DIR / "ceo-inbox"
    if not inbox_dir.exists():
        return []

    files = []
    for f in inbox_dir.glob("*.md"):
        if f.name != "TEMPLATE.md":
            files.append(f)
    return sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)


def parse_frontmatter(content: str) -> Dict[str, Any]:
    """Parse YAML frontmatter from markdown content."""
    if not content.startswith("---"):
        return {}

    try:
        end = content.find("---", 3)
        if end == -1:
            return {}

        frontmatter = content[3:end].strip()
        result = {}
        for line in frontmatter.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()
                # Handle null/none values
                if value.lower() in ("null", "none", "~", ""):
                    value = None
                result[key] = value
        return result
    except Exception:
        return {}


# ============================================================================
# MCP Tools
# ============================================================================

@mcp.tool(
    name="elf_query",
    annotations={
        "title": "Query ELF Building",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def elf_query(params: QueryInput) -> str:
    """
    Query the Emergent Learning Framework for context.

    Returns golden rules, heuristics, learnings, and other knowledge
    relevant to the current task. This is the primary way to load
    institutional knowledge before starting work.

    Args:
        params: Query parameters including domain, depth, and max_tokens

    Returns:
        Formatted context string with tiered knowledge:
        - Tier 1: Golden rules (always included)
        - Tier 2: Domain-specific heuristics and learnings
        - Tier 3: Recent context and experiments (deep mode)
    """
    try:
        qs = await get_query_system()

        context = await qs.build_context(
            task="Agent task context generation",
            domain=params.domain,
            max_tokens=params.max_tokens,
            depth=params.depth.value
        )

        await qs.cleanup()
        return context

    except Exception as e:
        return f"Error querying ELF: {type(e).__name__}: {str(e)}"


@mcp.tool(
    name="elf_record_heuristic",
    annotations={
        "title": "Record ELF Heuristic",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
async def elf_record_heuristic(params: RecordHeuristicInput) -> str:
    """
    Record a new heuristic in the Emergent Learning Framework.

    Heuristics are reusable rules of thumb discovered through work.
    They should be actionable, specific, and testable.

    Args:
        params: Heuristic details including domain, rule, explanation,
                source type, and confidence level

    Returns:
        Success message with heuristic ID, or error message
    """
    try:
        # Import async models
        from query.models import (
            get_manager,
            initialize_database,
            Heuristic
        )

        # Initialize database
        db_path = BASE_DIR / "memory" / "index.db"
        await initialize_database(str(db_path))

        # Create heuristics directory if needed
        heuristics_dir = BASE_DIR / "memory" / "heuristics"
        heuristics_dir.mkdir(parents=True, exist_ok=True)

        # Sanitize domain
        domain = params.domain.lower().replace(' ', '-')
        domain = re.sub(r'[^a-z0-9-]', '', domain).strip('-')

        # Insert into database using async API
        m = get_manager()
        async with m:
            async with m.connection():
                heuristic = await Heuristic.create(
                    domain=domain,
                    rule=params.rule,
                    explanation=params.explanation,
                    source_type=params.source.value,
                    confidence=params.confidence,
                    times_validated=0,
                    times_violated=0
                )

        # Append to domain markdown file
        domain_file = heuristics_dir / f"{domain}.md"

        if not domain_file.exists():
            header = f"""# Heuristics: {domain}

Generated from failures, successes, and observations in the **{domain}** domain.

---

"""
            with open(domain_file, 'w', encoding='utf-8') as f:
                f.write(header)

        entry = f"""## H-{heuristic.id}: {params.rule}

**Confidence**: {params.confidence}
**Source**: {params.source.value}
**Created**: {datetime.now().strftime('%Y-%m-%d')}

{params.explanation}

---

"""
        with open(domain_file, 'a', encoding='utf-8') as f:
            f.write(entry)

        return json.dumps({
            "success": True,
            "heuristic_id": heuristic.id,
            "domain": domain,
            "rule": params.rule,
            "confidence": params.confidence
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"{type(e).__name__}: {str(e)}"
        })


@mcp.tool(
    name="elf_record_failure",
    annotations={
        "title": "Record ELF Failure",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
async def elf_record_failure(params: RecordFailureInput) -> str:
    """
    Record a failure in the Emergent Learning Framework.

    Failures are valuable learning opportunities. Recording them
    immediately while context is fresh helps extract lessons and
    prevent similar issues in the future.

    Args:
        params: Failure details including title, domain, summary,
                severity (1-5), and optional tags

    Returns:
        Success message with failure ID and file path, or error message
    """
    try:
        # Import async models
        from query.models import (
            get_manager,
            initialize_database,
            Learning
        )

        # Initialize database
        db_path = BASE_DIR / "memory" / "index.db"
        await initialize_database(str(db_path))

        # Create failures directory if needed
        failures_dir = BASE_DIR / "memory" / "failures"
        failures_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        date_prefix = datetime.now().strftime("%Y%m%d")
        filename_title = re.sub(r'[^a-z0-9-]', '', params.title.lower().replace(' ', '-'))[:100]
        filename = f"{date_prefix}_{filename_title}.md"
        filepath = failures_dir / filename
        relative_path = f"memory/failures/{filename}"

        # Sanitize domain
        domain = params.domain.lower().replace(' ', '-')
        domain = re.sub(r'[^a-z0-9-]', '', domain)

        # Create markdown file
        markdown_content = f"""# {params.title}

**Domain**: {domain}
**Severity**: {params.severity}
**Tags**: {params.tags or ''}
**Date**: {datetime.now().strftime('%Y-%m-%d')}

## Summary

{params.summary}

## What Happened

[Describe the failure in detail]

## Root Cause

[What was the underlying issue?]

## Impact

[What were the consequences?]

## Prevention

[What heuristic or practice would prevent this?]

## Related

- **Experiments**:
- **Heuristics**:
- **Similar Failures**:
"""

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

        # Insert into database using async API
        m = get_manager()
        async with m:
            async with m.connection():
                learning = await Learning.create(
                    type='failure',
                    filepath=relative_path,
                    title=params.title,
                    summary=params.summary[:500] if params.summary else "",
                    tags=params.tags or "",
                    domain=domain,
                    severity=params.severity
                )

        return json.dumps({
            "success": True,
            "failure_id": learning.id,
            "filepath": str(filepath),
            "domain": domain,
            "severity": params.severity
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"{type(e).__name__}: {str(e)}"
        })


@mcp.tool(
    name="elf_ceo_inbox",
    annotations={
        "title": "Check ELF CEO Inbox",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def elf_ceo_inbox() -> str:
    """
    Check pending decisions in the CEO inbox.

    The CEO inbox contains items that require human decision-making,
    such as architectural choices, conflicting rules, or high-stakes
    decisions.

    Returns:
        JSON list of pending CEO reviews with status, priority,
        title, and summary for each item
    """
    try:
        inbox_files = get_ceo_inbox_files()

        items = []
        for filepath in inbox_files[:20]:  # Limit to 20 most recent
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

                frontmatter = parse_frontmatter(content)

                # Extract title from first heading
                title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
                title = title_match.group(1) if title_match else filepath.stem

                # Extract first paragraph of situation/context
                situation_match = re.search(r'##\s+Situation\s*\n+(.+?)(?=\n##|\n\n##|$)', content, re.DOTALL)
                summary = situation_match.group(1).strip()[:200] if situation_match else ""

                items.append({
                    "filename": filepath.name,
                    "title": title,
                    "status": frontmatter.get("status", "pending"),
                    "priority": frontmatter.get("priority", "medium"),
                    "domain": frontmatter.get("domain"),
                    "created": frontmatter.get("created"),
                    "summary": summary
                })
            except Exception:
                continue

        # Filter to pending items
        pending = [i for i in items if i.get("status") == "pending"]
        decided = [i for i in items if i.get("status") == "decided"]

        return json.dumps({
            "pending_count": len(pending),
            "decided_count": len(decided),
            "pending_items": pending,
            "recent_decided": decided[:5]  # Show 5 most recent decisions
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "error": f"{type(e).__name__}: {str(e)}",
            "pending_count": 0,
            "pending_items": []
        })


@mcp.tool(
    name="elf_search",
    annotations={
        "title": "Search ELF Knowledge",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def elf_search(params: SearchInput) -> str:
    """
    Search the ELF knowledge base for relevant information.

    Searches across heuristics, learnings, and failures to find
    knowledge relevant to a query.

    Args:
        params: Search parameters including query text, optional
                domain filter, and result limit

    Returns:
        JSON with matching heuristics and learnings
    """
    try:
        qs = await get_query_system()

        results = {
            "query": params.query,
            "domain": params.domain,
            "heuristics": [],
            "learnings": [],
            "similar_failures": []
        }

        # If domain is specified, query by domain
        if params.domain:
            domain_data = await qs.query_by_domain(params.domain, limit=params.limit)

            # Filter heuristics by keywords
            keywords = params.query.lower().split()
            for h in domain_data.get("heuristics", []):
                rule_lower = h.get("rule", "").lower()
                expl_lower = h.get("explanation", "").lower()
                if any(kw in rule_lower or kw in expl_lower for kw in keywords):
                    results["heuristics"].append({
                        "id": h.get("id"),
                        "domain": h.get("domain"),
                        "rule": h.get("rule"),
                        "explanation": (h.get("explanation") or "")[:200],
                        "confidence": h.get("confidence"),
                        "times_validated": h.get("times_validated")
                    })

            for l in domain_data.get("learnings", []):
                title_lower = l.get("title", "").lower()
                summary_lower = l.get("summary", "").lower()
                if any(kw in title_lower or kw in summary_lower for kw in keywords):
                    results["learnings"].append({
                        "id": l.get("id"),
                        "type": l.get("type"),
                        "domain": l.get("domain"),
                        "title": l.get("title"),
                        "summary": (l.get("summary") or "")[:200],
                        "tags": l.get("tags")
                    })

        # Find similar failures using QuerySystem
        try:
            similar = await qs.find_similar_failures(params.query, limit=5)
            for sf in similar:
                results["similar_failures"].append({
                    "title": sf.get("title", ""),
                    "similarity": sf.get("similarity", 0),
                    "matched_keywords": sf.get("matched_keywords", []),
                    "summary": (sf.get("summary") or "")[:200]
                })
        except Exception:
            pass  # Similar failures is optional

        # Query recent if no domain specified
        if not params.domain:
            try:
                recent = await qs.query_recent(limit=params.limit)
                keywords = params.query.lower().split()
                for item in recent:
                    title_lower = item.get("title", "").lower()
                    summary_lower = item.get("summary", "").lower()
                    if any(kw in title_lower or kw in summary_lower for kw in keywords):
                        results["learnings"].append({
                            "id": item.get("id"),
                            "type": item.get("type"),
                            "domain": item.get("domain"),
                            "title": item.get("title"),
                            "summary": (item.get("summary") or "")[:200],
                            "tags": item.get("tags")
                        })
            except Exception:
                pass

        await qs.cleanup()

        results["total_results"] = (
            len(results["heuristics"]) +
            len(results["learnings"]) +
            len(results["similar_failures"])
        )

        return json.dumps(results, indent=2)

    except Exception as e:
        return json.dumps({
            "error": f"{type(e).__name__}: {str(e)}",
            "query": params.query,
            "heuristics": [],
            "learnings": []
        })


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    mcp.run()
