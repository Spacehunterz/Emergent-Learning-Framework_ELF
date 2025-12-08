# Operations Guide

Production and team usage guide for ELF.

---

## Production Deployment

### Not Recommended for Production Runtime

ELF is designed for development environments. Claude Code runs on your local machine.

### Recommended Architecture

Production <- CI/CD <- Development + ELF (developers use ELF here)

---

## Team Usage Patterns

### Option 1: Individual Instances (Recommended)

Each developer runs their own ELF instance.

**Pros:** No coordination needed, personal learning
**Cons:** Learnings not shared automatically

**Setup:**
Each developer installs independently with ./install.sh
Periodically share heuristics via export/import

---

### Option 2: Project-Level Golden Rules

Share golden rules via project repository.

Create .claude/CLAUDE.md in project repo with team rules.

---

## Monitoring and Metrics

### Dashboard Metrics

Track team learning over time:
- Heuristics created per week
- Confidence score trends
- Violation rate
- Token cost per developer

### Database Health Checks

**Weekly:** Validate database integrity
**Monthly:** Vacuum database, prune low-value heuristics
**Quarterly:** Backup and archive old learnings

---

## Security Considerations

### Sensitive Data in Learnings

Review learnings before sharing to avoid leaking secrets.

### Database Encryption

Use encrypted filesystem or SQLCipher for database encryption.

### Access Control

Restrict database to owner-only: chmod 600 ~/.claude/emergent-learning/memory/index.db

---

## Backup and Recovery

### Backup Strategy

Backup these critical files:
- index.db (database)
- CLAUDE.md (if customized)
- ceo-inbox/ (decisions)

### Automated Backup

Create backup script and schedule with cron.

---

## Performance Tuning

### Database Optimization

Add indexes for frequent queries, run VACUUM regularly.

### Reducing Token Costs

Prune low-value heuristics, use domain-specific queries instead of full context.

---

## Best Practices

### Development Workflow

1. Start of day: check in to see recent learnings
2. During work: Let automatic learning happen
3. End of day: Review dashboard
4. Weekly: Prune low-confidence heuristics
5. Monthly: Share valuable heuristics with team

---

## Support and Maintenance

**Daily:** Automated backups
**Weekly:** Database validation
**Monthly:** Prune and vacuum
**Quarterly:** Full backup, review golden rules

---

*Last updated: 2025-12-08*
