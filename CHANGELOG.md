# Changelog

All notable changes to the Emergent Learning Framework will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-12-16

### Added
- Initial release of the Emergent Learning Framework
- Dashboard application for visualizing learning data
- Golden rules system for constitutional principles
- Heuristics tracking and validation
- Failure recording and analysis
- Success documentation
- CEO escalation workflow via ceo-inbox/
- Agent personas (Architect, Creative, Researcher, Skeptic)
- Multi-agent coordination support
- Database-backed memory system (SQLite)
- Session hooks for Claude Code integration
- Update mechanism (`update.sh`) for safe framework updates
  - Hybrid git/standalone support
  - Interactive conflict resolution
  - Customization detection via file hashes
  - Automatic backup and rollback on failure
  - Database migration support

### Infrastructure
- `install.sh` - One-command installation
- `update.sh` - Safe update mechanism
- `scripts/migrate_db.py` - Database migration runner
- `.stock-hashes` - Customization detection hashes

---

## Version History Notes

### Versioning Policy
- **Major (X.0.0)**: Breaking changes to configuration, database schema, or APIs
- **Minor (0.X.0)**: New features, backward-compatible
- **Patch (0.0.X)**: Bug fixes, documentation updates

### Upgrade Path
Use `update.sh` for all upgrades. It handles:
- Version checking
- Backup creation
- Customization detection
- Database migrations
- Rollback on failure

See [README.md](README.md) for detailed upgrade instructions.
