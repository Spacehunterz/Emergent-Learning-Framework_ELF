# ELF Use Cases

Real-world scenarios where the Emergent Learning Framework adds value.

---

## Use Case 1: Solo Developer on Long-Term Project

**Scenario:** You're building a SaaS application over 6 months. You use Claude Code for features, bug fixes, and refactoring.

### Without ELF
- Week 1: Claude suggests using JSON.parse() without try-catch. It crashes in production.
- Week 4: Different file, same mistake. You have to explain error handling again.
- Week 8: New developer onboarding. They make the same JSON.parse mistake.
- Week 12: You've explained the same patterns 15+ times across sessions.

### With ELF
- Week 1: JSON.parse crashes. You record: "Always wrap JSON.parse in try-catch"
- Week 2: Claude suggests JSON.parse. Pre-hook injects the heuristic. Code includes error handling automatically.
- Week 4: Heuristic confidence is now 0.8 after 5 validations. It's prioritized in relevant contexts.
- Week 8: New developer installs ELF, gets institutional knowledge instantly.
- Week 12: 15 patterns codified as golden rules. The codebase has a "style."

**Value:** Compound learning. Each mistake teaches the system permanently.

---

## Use Case 2: Team Collaboration on API Integration

**Scenario:** Team of 3 integrating with a flaky third-party payment API.

### The Problem
- API rate-limits aggressively (100 req/min)
- Timeout responses are inconsistent
- Retries can cause duplicate charges
- Documentation is outdated

### How ELF Helps

**Day 1: Alice discovers rate limit**
- Alice's Claude session hits rate limit
- Records failure: "Payment API has 100 req/min limit, implement backoff"

**Day 2: Bob works on retry logic**
- Bob's session queries building before implementing retries
- Sees Alice's rate limit learning
- Implements exponential backoff from the start

**Day 3: Carol adds timeout handling**
- Carol's session gets both learnings
- Implements: rate limiting + backoff + idempotency

**Value:** Team knowledge compounds. Each developer's learnings benefit everyone.

---

## Use Case 3: Debugging Complex Production Bug

**Scenario:** Production app has intermittent database deadlocks.

### Using Swarm (Multi-Agent)

Conductor spawns multiple perspectives:
1. **Researcher:** Examines transaction patterns
2. **Architect:** Reviews database schema
3. **Skeptic:** Tests edge cases

**Value:** Multi-perspective investigation speeds up complex debugging.

---

## Use Case 4: Security-Critical Project

**Scenario:** Building a healthcare app with HIPAA requirements.

### Golden Rules for Security
1. "Always sanitize user input before database queries"
2. "Log all PHI access with user ID and timestamp"
3. "Encrypt sensitive data before storage"

**How ELF Enforces:**
- Pre-hook injects security rules before every Task
- Violations are flagged in dashboard
- Audit trail for compliance

**Value:** Critical patterns enforced automatically.

---

## Use Case 5: Onboarding New Team Members

### Without ELF
- Week 1-4: Learning project quirks through trial and error

### With ELF
- Day 1: Install ELF, import team heuristics
- Day 2: Claude Code follows all team patterns automatically

**Value:** Onboarding time reduced from weeks to days.

---

## Anti-Patterns (When NOT to Use ELF)

1. **Quick One-Off Scripts** - Throwaway code you'll never touch again
2. **Learning Phase** - First week of new language/framework
3. **Highly Dynamic Projects** - Direction changes weekly
4. **Solo Scripts with No Reuse** - One-time data migrations

---

## Measuring Value

| Timeline | Learnings | Heuristics | Value |
|----------|-----------|------------|-------|
| Week 1 | 10-20 | 2-5 | Not obvious yet |
| Week 4 | 50-100 | 5-10 confidence >0.7 | Patterns auto-injected |
| Month 3 | 200+ | 3-5 golden rules | Clear time savings |
| Month 6 | 500+ | 10+ golden rules | Institutional memory |

**Bottom line:** ELF pays off when patterns repeat. The more you use it, the more it compounds.
