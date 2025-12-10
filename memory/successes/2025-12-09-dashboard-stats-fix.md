# Success: Fixed ELF Dashboard Stats and Click Handlers

**Date:** 2025-12-09
**Domain:** dashboard, frontend, backend

## Context
User reported two issues with the ELF dashboard:
1. Stats cards didn't navigate anywhere on click
2. Success rate was calculated incorrectly (using learnings table instead of workflow_runs status)

## Solution

### 1. Fixed Success Rate Calculation
**Backend (main.py):** Added proper queries to count workflow_runs by status:
```python
# Get actual run success/failure counts from workflow_runs status
cursor.execute("SELECT COUNT(*) FROM workflow_runs WHERE status = 'completed'")
stats["successful_runs"] = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM workflow_runs WHERE status IN ('failed', 'cancelled')")
stats["failed_runs"] = cursor.fetchone()[0]
```

**Frontend (App.tsx):** Updated statsForBar to use the correct fields:
```typescript
successful_runs: stats.successful_runs ?? stats.successes,
failed_runs: stats.failed_runs ?? stats.failures,
success_rate: stats.total_runs > 0 ? (stats.successful_runs ?? stats.successes) / stats.total_runs : 0,
```

### 2. Added Click-to-Navigate on Stats Cards
**StatsBar.tsx:** Added `onCardClick` prop and `tab` property to each stat card:
- Total Runs → runs tab
- Success Rate → runs tab
- Successful → runs tab
- Failed → runs tab
- Heuristics → heuristics tab
- Golden Rules → heuristics tab
- Hotspots → overview tab
- Today → timeline tab

**App.tsx:** Wired up click handler:
```typescript
<StatsBar stats={statsForBar} onCardClick={(tab) => setActiveTab(tab as any)} />
```

## Key Learning
When calculating metrics like success rate, ensure you're using the right data source:
- `learnings` table contains manually recorded successes/failures
- `workflow_runs.status` contains actual execution outcomes
These can have very different counts and mixing them produces nonsensical results.

## Files Modified
- `dashboard-app/backend/main.py` - Added successful_runs, failed_runs queries
- `dashboard-app/frontend/src/App.tsx` - Updated Stats interface and statsForBar calculation
- `dashboard-app/frontend/src/components/StatsBar.tsx` - Added click handlers and tab navigation
