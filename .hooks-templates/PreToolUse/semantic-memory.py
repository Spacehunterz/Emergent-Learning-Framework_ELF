#!/usr/bin/env python3
"""
Pre-Tool Semantic Memory Hook: Mid-stream context injection based on thinking blocks.

This hook implements mid-stream semantic memory injection:
1. Extract the last ~1500 chars from the most recent thinking block
2. Embed this current intent/context  
3. Pull relevant heuristics from vector DB
4. Inject them synchronously before tool execution

The result: Self-correcting Claude workflows that stay relevant as context drifts.
"""

import json
import sys
import os
from pathlib import Path
from typing import List, Dict, Optional, Any

# Add ELF src to path (works both in dev and installed)
script_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(script_dir / ".." / ".." / ".." / "src" / "query"))

# Import semantic search
try:
    from semantic_search import SemanticSearcher
    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False

# Constants
THINKING_CHARS = 1500  # Characters to extract from thinking block


def get_hook_input() -> dict:
    """Read hook input from stdin."""
    try:
        return json.load(sys.stdin)
    except (json.JSONDecodeError, IOError, ValueError):
        return {}


def read_transcript_thinking(transcript_path: str) -> Optional[str]:
    """
    Read the most recent thinking block from transcript.
    
    Returns the last ~1500 characters of the most recent thinking content,
    or None if no thinking block found.
    """
    if not transcript_path or not Path(transcript_path).exists():
        return None
    
    try:
        thinking_blocks = []
        
        with open(transcript_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                    
                try:
                    entry = json.loads(line)
                    
                    # Look for thinking blocks in various formats
                    # Format 1: Claude Code's thinking block format
                    if entry.get('role') == 'assistant' and entry.get('thinking'):
                        thinking_content = entry.get('thinking', '')
                        if isinstance(thinking_content, str):
                            thinking_blocks.append(thinking_content)
                    
                    # Format 2: Nested in content
                    content = entry.get('content', '')
                    if isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict):
                                if item.get('type') == 'thinking':
                                    thinking_text = item.get('thinking', '')
                                    if thinking_text:
                                        thinking_blocks.append(thinking_text)
                                # Alternative: thinking in text field
                                elif item.get('type') == 'text':
                                    text = item.get('text', '')
                                    # Check for explicit thinking markers
                                    if '<thinking>' in text or 'thinking_block' in text:
                                        thinking_blocks.append(text)
                    
                    # Format 3: Direct thinking field at top level
                    if entry.get('thinking_block') or entry.get('thinking_content'):
                        thinking = entry.get('thinking_block') or entry.get('thinking_content')
                        if thinking:
                            thinking_blocks.append(str(thinking))
                            
                except json.JSONDecodeError:
                    continue
        
        if not thinking_blocks:
            return None
            
        # Get the most recent thinking block
        latest_thinking = thinking_blocks[-1]
        
        # Return last THINKING_CHARS characters
        if len(latest_thinking) > THINKING_CHARS:
            return "..." + latest_thinking[-THINKING_CHARS:]
        return latest_thinking
        
    except Exception as e:
        # Silently fail - don't disrupt workflow
        return None


async def get_semantic_heuristics(
    thinking_context: str,
    tool_name: str,
    tool_input: dict
) -> List[Dict[str, Any]]:
    """
    Get semantically relevant heuristics based on thinking context.
    
    Uses embedding similarity between current thinking and heuristics DB.
    """
    if not SEMANTIC_AVAILABLE:
        return []
        
    try:
        # Initialize semantic searcher
        searcher = await SemanticSearcher.create()
        
        # Create rich query from thinking + tool context
        query = f"""
{thinking_context}

Tool: {tool_name}
Tool Input: {json.dumps(tool_input, default=str)[:500]}
""".strip()
        
        # Search for relevant heuristics
        results = await searcher.find_relevant_heuristics(
            task=query,
            threshold=0.65,  # Slightly lower threshold for mid-stream
            limit=3  # Keep it concise for mid-stream injection
        )
        
        await searcher.cleanup()
        return results
        
    except Exception as e:
        # Fail silently - don't block workflow
        return []


def format_injection_context(heuristics: List[Dict]) -> str:
    """Format heuristics for injection into Claude's context."""
    if not heuristics:
        return ""
    
    lines = [
        "",
        "---",
        "## [Mid-Stream Memory] Relevant Patterns Detected",
        ""
    ]
    
    for h in heuristics:
        rule = h.get('rule', '')
        domain = h.get('domain', 'general')
        confidence = h.get('confidence', 0) * 100
        is_golden = h.get('is_golden', False)
        
        prefix = "⭐ GOLDEN" if is_golden else f"[{domain}]"
        lines.append(f"- {prefix} {rule} ({confidence:.0f}% confidence)")
    
    lines.extend(["---", ""])
    return "\n".join(lines)


async def main_async():
    """Async main hook logic."""
    hook_input = get_hook_input()
    
    tool_name = hook_input.get("tool_name", hook_input.get("tool"))
    tool_input = hook_input.get("tool_input", hook_input.get("input", {}))
    transcript_path = hook_input.get("transcript_path", "")
    
    # Only process investigation/modification tools
    RELEVANT_TOOLS = {
        "Task", "Bash", "Grep", "Read", "Glob", "Edit", "Write",
        "WebFetch", "WebSearch"
    }
    
    is_mcp_tool = tool_name.startswith("mcp__") if tool_name else False
    
    if not tool_name or (tool_name not in RELEVANT_TOOLS and not is_mcp_tool):
        # Not a relevant tool - approve silently
        print(json.dumps({"decision": "approve"}))
        return
    
    # Extract thinking from transcript
    thinking_context = read_transcript_thinking(transcript_path)
    
    if not thinking_context:
        # No thinking block found - fall back to standard behavior
        print(json.dumps({"decision": "approve"}))
        return
    
    # Get semantically relevant heuristics
    heuristics = await get_semantic_heuristics(thinking_context, tool_name, tool_input)
    
    if not heuristics:
        # No relevant heuristics found
        print(json.dumps({"decision": "approve"}))
        return
    
    # Format and inject context
    injection_context = format_injection_context(heuristics)
    
    # Return with additional context injection
    result = {
        "decision": "approve",
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": injection_context
        }
    }
    
    print(json.dumps(result))


def main():
    """Sync entry point."""
    import asyncio
    try:
        asyncio.run(main_async())
    except Exception as e:
        # Never block - fail open
        print(json.dumps({"decision": "approve"}))


if __name__ == "__main__":
    main()
