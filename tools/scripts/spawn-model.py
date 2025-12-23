#!/usr/bin/env python3
"""
Spawn Model - Multi-Model Task Executor for ELF

Spawns tasks to other AI CLI tools (gemini, codex) and captures results.
Integrates with ELF for learning recording.

Usage:
    python spawn-model.py --model gemini --prompt "Refactor this React component"
    python spawn-model.py --model codex --prompt "Review this code" --file src/app.tsx
    python spawn-model.py --auto --prompt "Large frontend refactor" --files src/**/*.tsx

Features:
    - Auto-routing based on task/file analysis
    - Output capture and formatting
    - Optional ELF learning recording
    - Token usage tracking
"""

import argparse
import subprocess
import sys
import os
import json
import yaml
import shlex
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

# Add query module to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src' / 'query'))

try:
    from model_detection import (
        detect_installed_models,
        suggest_model_for_task,
        load_routing_config
    )
except ImportError:
    print("Warning: Could not import model_detection module", file=sys.stderr)
    detect_installed_models = None


def run_gemini(prompt: str, timeout: int = 120) -> Dict[str, Any]:
    """Run a prompt through Gemini CLI."""
    try:
        # Use shell=True on Windows for proper .CMD file resolution
        use_shell = sys.platform == 'win32'
        result = subprocess.run(
            'gemini' if use_shell else ['gemini'],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=use_shell
        )
        return {
            'success': result.returncode == 0,
            'output': result.stdout,
            'error': result.stderr if result.returncode != 0 else None,
            'model': 'gemini'
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'output': None,
            'error': f'Timeout after {timeout}s',
            'model': 'gemini'
        }
    except FileNotFoundError:
        return {
            'success': False,
            'output': None,
            'error': 'gemini CLI not found',
            'model': 'gemini'
        }
    except Exception as e:
        return {
            'success': False,
            'output': None,
            'error': str(e),
            'model': 'gemini'
        }


def run_codex(prompt: str, timeout: int = 120, mode: str = 'exec') -> Dict[str, Any]:
    """Run a prompt through Codex CLI.

    Codex CLI usage: codex exec "your prompt here"
    For long prompts (>4000 chars), uses stdin to avoid command line limits.
    """
    try:
        # Use shell=True on Windows for proper .CMD file resolution
        use_shell = sys.platform == 'win32'

        # Windows has ~8191 char command line limit - use stdin for long prompts
        use_stdin = len(prompt) > 4000

        if use_stdin:
            # Use stdin for long prompts to avoid command line length limits
            if use_shell:
                cmd = f'codex {mode}'
            else:
                cmd = ['codex', mode]

            result = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=use_shell
            )
        else:
            # Short prompts can use command line args
            if use_shell:
                # Windows: escape the prompt for CMD shell
                escaped_prompt = prompt.replace('"', '\\"').replace('\n', ' ')
                cmd = f'codex {mode} "{escaped_prompt}"'
            else:
                # Unix: use shlex for proper escaping, or pass as list (safer)
                cmd = ['codex', mode, prompt]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=use_shell
            )

        # Extract just the response from codex output (skip headers)
        output = result.stdout
        if 'codex\n' in output:
            # Find the codex response after headers
            parts = output.split('codex\n')
            if len(parts) > 1:
                output = parts[-1].strip()

        return {
            'success': result.returncode == 0,
            'output': output,
            'error': result.stderr if result.returncode != 0 else None,
            'model': 'codex'
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'output': None,
            'error': f'Timeout after {timeout}s',
            'model': 'codex'
        }
    except FileNotFoundError:
        return {
            'success': False,
            'output': None,
            'error': 'codex CLI not found',
            'model': 'codex'
        }
    except Exception as e:
        return {
            'success': False,
            'output': None,
            'error': str(e),
            'model': 'codex'
        }


def update_token_usage(model: str, approx_tokens: int):
    """Update token usage tracking in routing config."""
    config_path = Path.home() / '.claude' / 'model-routing.yaml'
    if not config_path.exists():
        return

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        if 'session_usage' not in config:
            config['session_usage'] = {'claude': 0, 'gemini': 0, 'codex': 0}

        config['session_usage'][model] = config['session_usage'].get(model, 0) + approx_tokens

        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False)
    except Exception:
        pass  # Non-critical, silently fail


def record_model_learning(
    model: str,
    task: str,
    success: bool,
    output_quality: Optional[str] = None,
    notes: Optional[str] = None
):
    """Record a learning about model performance to ELF."""
    if not success:
        return  # Don't record failures as learnings

    try:
        # Try to import ELF recording
        scripts_path = Path(__file__).parent
        record_script = scripts_path / 'record-heuristic.py'

        if record_script.exists() and output_quality:
            # Only record if we have quality feedback
            rule = f"{model} performed well on: {task[:50]}..."
            explanation = f"Quality: {output_quality}. {notes or ''}"

            subprocess.run([
                sys.executable,
                str(record_script),
                '--domain', 'multi-model',
                '--rule', rule,
                '--explanation', explanation,
                '--source', 'observation',
                '--confidence', '0.6'
            ], capture_output=True, timeout=10)
    except Exception:
        pass  # Non-critical


def main():
    parser = argparse.ArgumentParser(
        description='Spawn tasks to other AI models (Gemini, Codex)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with specific model
  python spawn-model.py --model gemini --prompt "Explain this React pattern"

  # Auto-select model based on task
  python spawn-model.py --auto --prompt "Refactor frontend components" --files src/*.tsx

  # Codex code review
  python spawn-model.py --model codex --mode review --file src/app.tsx

  # Get JSON output
  python spawn-model.py --model gemini --prompt "..." --format json

  # Swarm integration - read prompt from file, write output to file
  python spawn-model.py --model gemini --prompt-file agent-prompt.md --output result.md
"""
    )

    parser.add_argument('--model', choices=['gemini', 'codex', 'auto'],
                       default='auto', help='Model to use (default: auto)')
    parser.add_argument('--prompt', help='The prompt/task to send')
    parser.add_argument('--prompt-file', type=Path,
                       help='Read prompt from file (for swarm integration)')
    parser.add_argument('--output', '--output-file', type=Path, dest='output',
                       help='Write output to file (for swarm integration)')
    parser.add_argument('--file', help='Single file to include in context')
    parser.add_argument('--files', nargs='+', help='Multiple files to include')
    parser.add_argument('--mode', default='exec',
                       help='Codex mode: exec, review (default: exec)')
    parser.add_argument('--timeout', type=int, default=120,
                       help='Timeout in seconds (default: 120)')
    parser.add_argument('--format', choices=['text', 'json'], default='text',
                       help='Output format (default: text)')
    parser.add_argument('--record', action='store_true',
                       help='Record result to ELF as learning')
    parser.add_argument('--quiet', action='store_true',
                       help='Suppress status messages')

    args = parser.parse_args()

    # Handle prompt from file (for swarm integration)
    prompt = args.prompt
    if args.prompt_file:
        if args.prompt_file.exists():
            prompt = args.prompt_file.read_text(encoding='utf-8')
        else:
            print(f"Error: Prompt file not found: {args.prompt_file}", file=sys.stderr)
            sys.exit(1)

    if not prompt:
        print("Error: No prompt provided (use --prompt or --prompt-file)", file=sys.stderr)
        sys.exit(1)

    # Collect files
    files = []
    if args.file:
        files.append(args.file)
    if args.files:
        files.extend(args.files)

    # Determine model
    model = args.model
    suggestion = None

    if model == 'auto':
        if detect_installed_models:
            models = detect_installed_models()
            suggestion = suggest_model_for_task(prompt, files, models)
            model = suggestion['suggested']

            if not args.quiet:
                print(f"Auto-selected: {model}", file=sys.stderr)
                print(f"Reason: {suggestion['reason']}", file=sys.stderr)
                print(f"Confidence: {suggestion['confidence']:.0%}", file=sys.stderr)
                print("---", file=sys.stderr)
        else:
            model = 'claude'
            if not args.quiet:
                print("Auto-detection unavailable, defaulting to claude", file=sys.stderr)

    # Build full prompt with file contents if provided
    full_prompt = prompt
    if files:
        full_prompt += "\n\n---\nFiles:\n"
        for filepath in files:
            try:
                p = Path(filepath)
                if p.exists():
                    content = p.read_text(encoding='utf-8', errors='replace')
                    full_prompt += f"\n### {filepath}\n```\n{content}\n```\n"
            except Exception as e:
                full_prompt += f"\n### {filepath}\n(Error reading: {e})\n"

    # Run the model
    if model == 'gemini':
        result = run_gemini(full_prompt, args.timeout)
    elif model == 'codex':
        result = run_codex(full_prompt, args.timeout, args.mode)
    elif model == 'claude':
        # Claude is the current session - just return the prompt for it to handle
        result = {
            'success': True,
            'output': f"[Route to Claude - current session]\n\nTask: {prompt}",
            'error': None,
            'model': 'claude'
        }
    else:
        result = {
            'success': False,
            'output': None,
            'error': f'Unknown model: {model}',
            'model': model
        }

    # Add suggestion info if available
    if suggestion:
        result['suggestion'] = suggestion

    # Update token tracking
    if result['output']:
        approx_tokens = len(result['output']) // 4
        update_token_usage(model, approx_tokens)

    # Record learning if requested
    if args.record and result['success']:
        record_model_learning(model, prompt, True)

    # Write output to file if specified (for swarm integration)
    if args.output:
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            if result['success']:
                args.output.write_text(result['output'], encoding='utf-8')
            else:
                args.output.write_text(f"ERROR: {result['error']}", encoding='utf-8')
            if not args.quiet:
                print(f"Output written to: {args.output}", file=sys.stderr)
        except Exception as e:
            print(f"Error writing output file: {e}", file=sys.stderr)

    # Output result (also print to stdout unless quiet)
    if args.format == 'json':
        print(json.dumps(result, indent=2))
    else:
        if result['success']:
            print(result['output'])
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)


if __name__ == '__main__':
    main()
