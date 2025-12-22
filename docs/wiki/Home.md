# Emergent Learning Framework Wiki

Welcome to the ELF documentation. This wiki contains detailed guides for all features.

## Quick Links

| Page | Description |
|------|-------------|
| [Installation](Installation) | Prerequisites, install options, troubleshooting |
| [Configuration](Configuration) | CLAUDE.md, settings.json, hooks setup |
| [Dashboard](Dashboard) | Visual monitoring, tabs, themes |
| [Swarm](Swarm) | Multi-agent coordination, personas |
| [CLI Reference](CLI-Reference) | All query commands |
| [Golden Rules](Golden-Rules) | Customizing constitutional principles |
| [Migration](Migration) | Upgrading, team setup, rollback |
| [Architecture](Architecture) | Database schema, hooks system |
| [Token Costs](Token-Costs) | Usage breakdown, optimization tips |

## The Core Concept

Claude Code is stateless - every session starts from zero. This framework bridges that gap by giving Claude access to your project's history:

- **Before each task:** Query the building for relevant knowledge
- **After each task:** Record outcomes automatically
- **Over time:** Patterns strengthen, mistakes don't repeat

## The Learning Loop

```
QUERY   ->  Check building for knowledge
APPLY   ->  Use heuristics during task
RECORD  ->  Capture outcome (success/failure)
PERSIST ->  Update confidence scores
            |
         (cycle repeats)
```

## What It's NOT

- **Not AI training** - Claude's model doesn't change. This is structured context injection.
- **Not magic** - It's systematic note-taking with automatic retrieval.
- **Not instant value** - It compounds over time. Day one won't feel different.
