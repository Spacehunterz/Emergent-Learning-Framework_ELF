#!/usr/bin/env python3
"""
Multi-Model Detection and Routing for Emergent Learning Framework

Detects installed AI CLI tools and provides routing recommendations
based on task characteristics and model strengths.
"""

import subprocess
import shutil
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml


# Default routing config embedded for when no config file exists
DEFAULT_ROUTING_CONFIG = {
    'models': {
        'claude': {
            'cli': 'claude',
            'default': True,
            'strengths': [
                'backend',
                'architecture',
                'orchestration',
                'nuanced-reasoning',
                'elf-integration',
                'complex-refactoring',
                'api-design'
            ],
            'weaknesses': [],
            'max_context': 200000,
            'notes': 'Primary orchestrator, handles ELF integration'
        },
        'gemini': {
            'cli': 'gemini',
            'default': False,
            'strengths': [
                'frontend',
                'react',
                'vue',
                'svelte',
                'css',
                'styling',
                'large-codebase',
                'ui-components'
            ],
            'weaknesses': [],
            'max_context': 1000000,
            'notes': '1M context window, excellent for large frontend refactors'
        },
        'codex': {
            'cli': 'codex',
            'default': False,
            'strengths': [
                'precision-tasks',
                'graphics',
                'integration',
                'debugging',
                'code-review',
                'svg',
                'canvas',
                'visualization'
            ],
            'weaknesses': [],
            'max_context': 128000,
            'notes': 'GPT-5.2, precise and good at graphics/visualization'
        }
    },
    'routing_rules': [
        {
            'pattern': r'\.(tsx|jsx|vue|svelte)$',
            'prefer': 'gemini',
            'reason': 'Frontend component files'
        },
        {
            'pattern': r'\.(css|scss|less|styled)$',
            'prefer': 'gemini',
            'reason': 'Styling files'
        },
        {
            'pattern': r'(svg|canvas|chart|graph|visual)',
            'prefer': 'codex',
            'reason': 'Graphics/visualization work'
        },
        {
            'pattern': r'(api|server|backend|database|sql)',
            'prefer': 'claude',
            'reason': 'Backend/API work'
        }
    ],
    'thresholds': {
        'large_codebase_files': 50,  # Route to gemini if > 50 files
        'token_balance_threshold': 0.7  # Rebalance if one model has 70%+ usage
    }
}


def get_cli_version(cli_name: str) -> Optional[str]:
    """Get the version of an installed CLI tool."""
    try:
        # Try common version flags
        for flag in ['--version', '-v', '-V', 'version']:
            try:
                result = subprocess.run(
                    [cli_name, flag],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                output = result.stdout.strip()
                if not output:
                    output = result.stderr.strip()
                
                if output:
                    # Extract version number from output
                    version_match = re.search(r'(\d+\.\d+(\.\d+)?)', output)
                    if version_match:
                        return version_match.group(1)
                    return output.split('\n')[0][:50].strip()  # First line, truncated
            except subprocess.TimeoutExpired:
                continue
            except Exception:
                continue
        return "installed"  # Found but couldn't get version
    except Exception:
        return None


def detect_installed_models() -> Dict[str, Dict[str, Any]]:
    """
    Detect which AI CLI tools are installed and available.

    Returns:
        Dictionary with model info: {
            'gemini': {'installed': True, 'version': '0.15.3', 'path': '/path/to/gemini'},
            'codex': {'installed': True, 'version': '0.76.0', 'path': '/path/to/codex'},
            'claude': {'installed': True, 'version': 'current', 'path': None}
        }
    """
    models = {}

    # Check gemini
    gemini_path = shutil.which('gemini')
    if gemini_path:
        models['gemini'] = {
            'installed': True,
            'version': get_cli_version('gemini'),
            'path': gemini_path,
            'max_context': 1000000,
            'strengths': ['frontend', 'large-context', 'react', 'vue', 'css']
        }
    else:
        models['gemini'] = {'installed': False}

    # Check codex (OpenAI)
    codex_path = shutil.which('codex')
    if codex_path:
        models['codex'] = {
            'installed': True,
            'version': get_cli_version('codex'),
            'path': codex_path,
            'max_context': 128000,
            'strengths': ['precision', 'graphics', 'debugging', 'code-review']
        }
    else:
        models['codex'] = {'installed': False}

    # Claude is always available (we're running in it)
    models['claude'] = {
        'installed': True,
        'version': 'current',
        'path': None,  # Current session
        'max_context': 200000,
        'strengths': ['backend', 'architecture', 'orchestration', 'elf-integration']
    }

    return models


def load_routing_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load routing configuration from YAML file or use defaults."""
    if config_path is None:
        config_path = Path.home() / '.claude' / 'model-routing.yaml'

    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception:
            pass

    return DEFAULT_ROUTING_CONFIG


def format_models_for_context(models: Dict[str, Dict[str, Any]]) -> str:
    """Format detected models for inclusion in ELF context output."""
    lines = []
    lines.append("## Available AI Models\n")

    installed = [(name, info) for name, info in models.items() if info.get('installed')]
    not_installed = [(name, info) for name, info in models.items() if not info.get('installed')]

    if installed:
        for name, info in installed:
            version = info.get('version', 'unknown')
            max_ctx = info.get('max_context', 0)
            ctx_str = f"{max_ctx // 1000}K" if max_ctx else ""
            strengths = info.get('strengths', [])
            strengths_str = ', '.join(strengths[:3]) if strengths else ''

            if name == 'claude':
                lines.append(f"- **claude** (current session) [active] orchestrator")
            else:
                lines.append(f"- **{name}** v{version} [ready] {ctx_str} context | {strengths_str}")

    if not_installed:
        not_installed_names = [name for name, _ in not_installed]
        lines.append(f"\nNot installed: {', '.join(not_installed_names)}")

    lines.append("")
    return '\n'.join(lines)


def suggest_model_for_task(
    task_description: str,
    files: Optional[List[str]] = None,
    models: Optional[Dict[str, Dict[str, Any]]] = None,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Suggest the best model for a given task.

    Args:
        task_description: What the task involves
        files: Optional list of files involved
        models: Detected models (will detect if not provided)
        config: Routing config (will load if not provided)

    Returns:
        {
            'suggested': 'gemini',
            'reason': 'Large frontend refactor with 50+ files',
            'alternatives': ['claude', 'codex'],
            'confidence': 0.8
        }
    """
    if models is None:
        models = detect_installed_models()
    if config is None:
        config = load_routing_config()

    # Only consider installed models
    available = {k: v for k, v in models.items() if v.get('installed')}

    if not available:
        return {
            'suggested': 'claude',
            'reason': 'No external models available',
            'alternatives': [],
            'confidence': 1.0
        }

    task_lower = task_description.lower()
    scores = {name: 0.0 for name in available}
    reasons = {name: [] for name in available}

    # Score based on keywords in task
    keyword_mappings = {
        'frontend': ('gemini', 0.3),
        'react': ('gemini', 0.3),
        'vue': ('gemini', 0.3),
        'svelte': ('gemini', 0.3),
        'css': ('gemini', 0.2),
        'styling': ('gemini', 0.2),
        'component': ('gemini', 0.2),
        'ui': ('gemini', 0.2),
        'backend': ('claude', 0.3),
        'api': ('claude', 0.3),
        'server': ('claude', 0.3),
        'database': ('claude', 0.3),
        'architecture': ('claude', 0.3),
        'refactor': ('claude', 0.2),
        'graphics': ('codex', 0.3),
        'svg': ('codex', 0.3),
        'canvas': ('codex', 0.3),
        'chart': ('codex', 0.3),
        'visualization': ('codex', 0.3),
        'debug': ('codex', 0.2),
        'review': ('codex', 0.2),
        'precise': ('codex', 0.2),
    }

    for keyword, (model, score) in keyword_mappings.items():
        if keyword in task_lower and model in scores:
            scores[model] += score
            reasons[model].append(f"'{keyword}' in task")

    # Score based on file types if provided
    if files:
        file_count = len(files)
        frontend_files = sum(1 for f in files if re.search(r'\.(tsx|jsx|vue|svelte|css|scss)$', f))
        backend_files = sum(1 for f in files if re.search(r'\.(py|go|rs|java|sql)$', f))

        if frontend_files > backend_files and 'gemini' in scores:
            scores['gemini'] += 0.2
            reasons['gemini'].append(f"{frontend_files} frontend files")

        if backend_files > frontend_files and 'claude' in scores:
            scores['claude'] += 0.2
            reasons['claude'].append(f"{backend_files} backend files")

        # Large codebase → prefer gemini for context window
        threshold = config.get('thresholds', {}).get('large_codebase_files', 50)
        if file_count > threshold and 'gemini' in scores:
            scores['gemini'] += 0.3
            reasons['gemini'].append(f"{file_count} files (large codebase)")

    # Claude gets a small boost as default orchestrator
    if 'claude' in scores:
        scores['claude'] += 0.1
        reasons['claude'].append('default orchestrator')

    # Find best model
    if not scores:
        return {
            'suggested': 'claude',
            'reason': 'Default fallback',
            'alternatives': [],
            'confidence': 0.5
        }

    sorted_models = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_model, best_score = sorted_models[0]
    alternatives = [m for m, _ in sorted_models[1:] if scores[m] > 0]

    # Normalize confidence
    confidence = min(best_score / 1.0, 1.0)  # Cap at 1.0

    reason_parts = reasons[best_model][:3]  # Top 3 reasons
    reason = ', '.join(reason_parts) if reason_parts else 'best available'

    return {
        'suggested': best_model,
        'reason': reason,
        'alternatives': alternatives,
        'confidence': confidence
    }


if __name__ == '__main__':
    # Test detection
    print("Detecting installed models...")
    models = detect_installed_models()
    print(format_models_for_context(models))

    # Test routing
    print("\nTesting routing suggestions:")
    test_tasks = [
        "Refactor the React frontend components",
        "Design the API backend architecture",
        "Create an SVG visualization for the data",
        "Review and debug this code"
    ]

    for task in test_tasks:
        suggestion = suggest_model_for_task(task, models=models)
        print(f"\nTask: {task}")
        print(f"  Suggested: {suggestion['suggested']} ({suggestion['confidence']:.0%})")
        print(f"  Reason: {suggestion['reason']}")
