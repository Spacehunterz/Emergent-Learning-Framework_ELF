#!/bin/bash
set -e

AGENTS_DIR="$HOME/.claude/agents"
COMMANDS_DIR="$HOME/.claude/commands"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ELF_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "=== ELF Agent Pool Installer ==="
echo ""

if [ -d "$AGENTS_DIR" ]; then
    echo "Agents directory exists at $AGENTS_DIR"
    read -p "Update to latest? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cd "$AGENTS_DIR"
        git pull origin main
        echo "✓ Updated agents"
    else
        echo "Skipping agent update"
    fi
else
    echo "Cloning wshobson/agents..."
    git clone https://github.com/wshobson/agents.git "$AGENTS_DIR"
    echo "✓ Cloned agents to $AGENTS_DIR"
fi

echo ""
echo "Creating agent catalog..."
cat > "$AGENTS_DIR/agent-catalog.json" << 'CATALOG'
{
  "version": "1.0.0",
  "source": "wshobson/agents",
  "agent_count": 100,
  "categories": {
    "backend": {
      "description": "API design, backend architecture, microservices",
      "agents": ["backend-architect", "graphql-architect", "fastapi-pro", "django-pro", "event-sourcing-architect"]
    },
    "frontend": {
      "description": "Frontend, mobile, UI/UX development",
      "agents": ["frontend-developer", "mobile-developer", "flutter-expert", "ios-developer", "ui-ux-designer"]
    },
    "infrastructure": {
      "description": "Cloud, DevOps, Kubernetes, deployment",
      "agents": ["cloud-architect", "kubernetes-architect", "terraform-specialist", "deployment-engineer", "devops-troubleshooter", "hybrid-cloud-architect", "network-engineer", "service-mesh-expert"]
    },
    "security": {
      "description": "Security auditing, threat modeling, hardening",
      "agents": ["security-auditor", "threat-modeling-expert", "backend-security-coder", "frontend-security-coder", "mobile-security-coder"]
    },
    "database": {
      "description": "Database design, optimization, migrations",
      "agents": ["database-architect", "database-optimizer", "database-admin", "sql-pro", "data-engineer"]
    },
    "quality": {
      "description": "Code review, testing, refactoring",
      "agents": ["code-reviewer", "test-automator", "architect-review", "legacy-modernizer", "tdd-orchestrator"]
    },
    "ai_ml": {
      "description": "AI/ML, LLM development, data science",
      "agents": ["ai-engineer", "prompt-engineer", "vector-database-engineer", "data-scientist", "ml-engineer", "mlops-engineer"]
    },
    "debugging": {
      "description": "Error analysis, debugging, diagnostics",
      "agents": ["debugger", "error-detective", "incident-responder", "dx-optimizer"]
    },
    "documentation": {
      "description": "Documentation, diagrams, tutorials",
      "agents": ["docs-architect", "api-documenter", "mermaid-expert", "tutorial-engineer", "reference-builder"]
    },
    "languages": {
      "description": "Language specialists",
      "agents": ["python-pro", "typescript-pro", "javascript-pro", "rust-pro", "golang-pro", "java-pro", "csharp-pro", "scala-pro", "cpp-pro", "c-pro", "ruby-pro", "php-pro", "elixir-pro", "haskell-pro", "julia-pro", "bash-pro", "posix-shell-pro"]
    },
    "specialized": {
      "description": "Domain-specific specialists",
      "agents": ["blockchain-developer", "quant-analyst", "risk-manager", "payment-integration", "unity-developer", "minecraft-bukkit-pro", "arm-cortex-expert"]
    },
    "observability": {
      "description": "Monitoring, metrics, performance",
      "agents": ["observability-engineer", "performance-engineer"]
    },
    "architecture": {
      "description": "C4 diagrams, architecture documentation",
      "agents": ["c4-code", "c4-component", "c4-container", "c4-context", "monorepo-architect"]
    },
    "business": {
      "description": "Business, HR, legal, sales, marketing",
      "agents": ["business-analyst", "hr-pro", "legal-advisor", "customer-support", "sales-automator", "content-marketer", "search-specialist"]
    },
    "seo": {
      "description": "SEO optimization and content",
      "agents": ["seo-content-writer", "seo-content-planner", "seo-content-auditor", "seo-meta-optimizer", "seo-keyword-strategist", "seo-structure-architect", "seo-snippet-hunter", "seo-content-refresher", "seo-cannibalization-detector", "seo-authority-builder"]
    }
  }
}
CATALOG
echo "✓ Created agent catalog"

echo ""
echo "Installing /swarm command..."
mkdir -p "$COMMANDS_DIR"
cp "$ELF_ROOT/library/commands/swarm.md" "$COMMANDS_DIR/swarm.md"
echo "✓ Installed swarm command"

AGENT_COUNT=$(find "$AGENTS_DIR/plugins" -path "*/agents/*.md" -type f 2>/dev/null | xargs -I {} basename {} .md | sort -u | wc -l)

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Agents installed: $AGENT_COUNT"
echo "Location: $AGENTS_DIR"
echo "Catalog: $AGENTS_DIR/agent-catalog.json"
echo "Swarm: $COMMANDS_DIR/swarm.md"
echo ""
echo "Usage: /swarm <task>"
