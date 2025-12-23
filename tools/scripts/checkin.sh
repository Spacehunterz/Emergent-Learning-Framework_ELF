#!/bin/bash
# ELF Checkin - Load building context and run checkin workflow

set -e

# Show banner
echo ""
echo "┌────────────────────────────────────┐"
echo "│    Emergent Learning Framework     │"
echo "├────────────────────────────────────┤"
echo "│                                    │"
echo "│      █████▒  █▒     █████▒         │"
echo "│      █▒      █▒     █▒             │"
echo "│      ████▒   █▒     ████▒          │"
echo "│      █▒      █▒     █▒             │"
echo "│      █████▒  █████▒ █▒             │"
echo "│                                    │"
echo "└────────────────────────────────────┘"
echo ""

# Step 1: Run query system to load context
echo "🏢 Loading Building Context..."
python ~/.claude/emergent-learning/query/query.py --context

# Step 2: Ask about dashboard
echo ""
read -p "🚀 Start ELF Dashboard? [Y/n]: " -n 1 -r dashboard_choice
echo ""
if [[ "$dashboard_choice" =~ ^[Yy]?$ ]]; then
    echo "Launching dashboard..."
    bash ~/.claude/emergent-learning/dashboard-app/run-dashboard.sh &
fi

# Step 3: Ask about multi-model support
echo ""
echo "🤖 Multi-Model Support Available"
echo "Available models:"
echo "  - gemini (1000K context, frontend/React optimized)"
echo "  - codex (128K context, precision/debugging optimized)"  
echo "  - claude (active, orchestrator)"
echo ""
read -p "Show multi-model setup? [Y/n]: " -n 1 -r model_choice
echo ""
if [[ "$model_choice" =~ ^[Yy]?$ ]]; then
    echo ""
    echo "To switch models, set ELF_MODEL environment variable:"
    echo "  export ELF_MODEL=gemini"
    echo ""
fi

echo "✅ Checkin complete. Ready to work!"
echo ""
