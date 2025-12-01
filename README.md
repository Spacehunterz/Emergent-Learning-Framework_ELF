# Emergent Learning Framework

A systematic approach to learning from failures, extracting heuristics, and running deliberate experiments.

## Directory Structure

```
emergent-learning/
├── memory/              # The knowledge base
│   ├── failures/        # Documented failures
│   ├── successes/       # Documented successes
│   ├── heuristics/      # Extracted rules by domain
│   ├── schema.sql       # Database schema
│   └── index.db         # SQLite index
├── experiments/         # Active learning experiments
│   ├── active/          # Currently running
│   └── completed/       # Finished experiments
├── cycles/              # Try/Break cycle logs
├── ceo-inbox/           # Decisions requiring human input
├── agents/              # Agent configurations
├── logs/                # Execution logs
├── query/               # Query tools and dashboards
└── scripts/             # Helper scripts
```

## Quick Start

### Initialize the Framework

```bash
./scripts/init.sh         # Bash
./scripts/init.ps1        # PowerShell
```

### Record a Failure

```bash
./scripts/record-failure.sh      # Bash
./scripts/record-failure.ps1     # PowerShell
```

### Record a Heuristic

```bash
./scripts/record-heuristic.sh    # Bash
./scripts/record-heuristic.ps1   # PowerShell
```

### Start an Experiment

```bash
./scripts/start-experiment.sh    # Bash
./scripts/start-experiment.ps1   # PowerShell
```

## Philosophy

1. **Fail Deliberately**: Create controlled experiments to test assumptions
2. **Extract Patterns**: Convert experiences into reusable heuristics
3. **Validate Continuously**: Track which rules prove helpful vs harmful
4. **Promote the Best**: Elevate proven heuristics to golden rules
5. **Stay Humble**: All knowledge is provisional and subject to revision

## The Learning Loop

```
Try → Break → Analyze → Extract → Validate → Promote
```

Every cycle adds to our collective intelligence.
