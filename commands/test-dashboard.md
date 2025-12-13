# /test-dashboard - Visual Dashboard Verification

Run browser automation tests against the ELF dashboard with visual evidence capture.

## Usage

```
/test-dashboard              # Quick smoke test
/test-dashboard full         # Full test with all tabs
/test-dashboard [tab]        # Test specific tab
/test-dashboard screenshot   # Capture current state only
```

## Prerequisites

- dev-browser server running: `~/.claude/skills/dev-browser/server.sh`
- Dashboard backend: `cd ~/.claude/emergent-learning/dashboard-app/backend && python -m uvicorn main:app --port 8888`
- Dashboard frontend: `cd ~/.claude/emergent-learning/dashboard-app/frontend && bun run dev`

---

## Instructions

### `/test-dashboard` (Quick Smoke Test)

1. **Check servers are running:**
   ```bash
   curl -s http://localhost:9222/ || echo "dev-browser not running"
   curl -s http://localhost:8888/api/stats || echo "Backend not running"
   ```

2. **Run quick verification:**
   ```bash
   cd ~/.claude/skills/dev-browser && bun x tsx <<'EOF'
   import { connect } from "./src/client.js";

   const client = await connect("http://localhost:9222");
   const page = await client.page("elf-test");
   await page.goto("http://localhost:3011");  // Adjust port as needed
   await page.waitForLoadState("networkidle");

   // Verify key elements
   const title = await page.title();
   console.log("Title:", title);

   const snapshot = await client.getAISnapshot("elf-test");

   // Check for critical elements
   const hasHeader = snapshot.includes("COSMIC DASHBOARD");
   const hasStats = snapshot.includes("Total Runs");
   const hasNav = snapshot.includes("Overview") && snapshot.includes("Heuristics");

   console.log("\n--- Smoke Test Results ---");
   console.log("Header:", hasHeader ? "PASS" : "FAIL");
   console.log("Stats:", hasStats ? "PASS" : "FAIL");
   console.log("Navigation:", hasNav ? "PASS" : "FAIL");

   if (!hasHeader || !hasStats || !hasNav) {
     await page.screenshot({ path: "tmp/smoke-test-failure.png" });
     console.log("\nScreenshot saved: tmp/smoke-test-failure.png");
   }

   await client.disconnect();
   EOF
   ```

3. **Report results** - If failures, suggest recording to `memory/failures/`

### `/test-dashboard full` (All Tabs)

Test each tab in sequence, capturing screenshots:

```bash
cd ~/.claude/skills/dev-browser && bun x tsx <<'EOF'
import { connect } from "./src/client.js";
import * as fs from "fs";

const TABS = [
  { name: "Overview", ref: "e14" },
  { name: "Heuristics", ref: "e18" },
  { name: "Assumptions", ref: "e23" },
  { name: "Spikes", ref: "e27" },
  { name: "Invariants", ref: "e34" },
  { name: "Graph", ref: "e39" },
  { name: "Runs", ref: "e46" },
  { name: "Sessions", ref: "e52" },
  { name: "Timeline", ref: "e58" },
  { name: "Analytics", ref: "e63" },
  { name: "Query", ref: "e68" }
];

const client = await connect("http://localhost:9222");
const page = await client.page("elf-full-test");
await page.goto("http://localhost:3011");
await page.waitForLoadState("networkidle");

const timestamp = new Date().toISOString().split('T')[0];
const results = [];

for (const tab of TABS) {
  try {
    // Click tab (refs may change - use text selector as fallback)
    await page.click(`text=${tab.name}`);
    await page.waitForTimeout(500);

    // Screenshot
    const filename = `tmp/dashboard-${tab.name.toLowerCase()}-${timestamp}.png`;
    await page.screenshot({ path: filename });

    results.push({ tab: tab.name, status: "PASS", screenshot: filename });
    console.log(`${tab.name}: PASS`);
  } catch (e) {
    results.push({ tab: tab.name, status: "FAIL", error: e.message });
    console.log(`${tab.name}: FAIL - ${e.message}`);
  }
}

console.log("\n--- Summary ---");
const passed = results.filter(r => r.status === "PASS").length;
console.log(`${passed}/${TABS.length} tabs passed`);

await client.disconnect();
EOF
```

### `/test-dashboard [tab]` (Specific Tab)

Test a single tab. Valid tabs: overview, heuristics, assumptions, spikes, invariants, graph, runs, sessions, timeline, analytics, query

```bash
# Example for heuristics tab:
cd ~/.claude/skills/dev-browser && bun x tsx <<'EOF'
import { connect } from "./src/client.js";

const client = await connect("http://localhost:9222");
const page = await client.page("elf-test");
await page.goto("http://localhost:3011");
await page.waitForLoadState("networkidle");

// Click specified tab
await page.click("text=Heuristics");
await page.waitForTimeout(500);

// Get snapshot for analysis
const snapshot = await client.getAISnapshot("elf-test");
console.log(snapshot);

// Screenshot
await page.screenshot({ path: "tmp/heuristics-test.png" });
await client.disconnect();
EOF
```

### `/test-dashboard screenshot` (Capture Only)

Capture current dashboard state without tests:

```bash
cd ~/.claude/skills/dev-browser && bun x tsx <<'EOF'
import { connect } from "./src/client.js";

const client = await connect("http://localhost:9222");
const page = await client.page("elf-capture");
await page.goto("http://localhost:3011");
await page.waitForLoadState("networkidle");

const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
await page.screenshot({
  path: `~/.claude/emergent-learning/memory/screenshots/dashboard-${timestamp}.png`,
  fullPage: true
});

console.log("Full-page screenshot captured");
await client.disconnect();
EOF
```

---

## Integration with Learning Cycle

When tests **FAIL**:
1. Screenshot automatically captured to `tmp/`
2. Copy evidence to `memory/screenshots/` with dated filename
3. Record failure: `bash ~/.claude/emergent-learning/scripts/record-failure.sh`
4. Attach screenshot path in the `## Visual Evidence` section

When tests **PASS**:
1. Confidence increases for visual-testing heuristics
2. Screenshots can be used as visual regression baselines

---

## Troubleshooting

**dev-browser not responding:**
```bash
# Kill and restart
pkill -f "dev-browser"
cd ~/.claude/skills/dev-browser && bash server.sh &
```

**Wrong port:**
Check what port frontend is using - it auto-increments if 3000 is busy.

**Element refs changed:**
Refs like `e14`, `e18` can change between page loads. Use text selectors as fallback:
```typescript
await page.click("text=Heuristics");
```
