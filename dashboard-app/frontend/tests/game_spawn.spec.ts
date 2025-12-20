import { test, expect } from '@playwright/test';

test('game loads and runs spawn logic on local dev', async ({ page }) => {
    const logs: string[] = [];
    page.on('console', msg => {
        const text = msg.text();
        logs.push(text);
        console.log('PAGE LOG:', text);
    });
    page.on('pageerror', err => console.log('PAGE ERROR:', err.message));

    // Use 5173
    await page.goto('http://localhost:5173');

    const canvas = page.locator('canvas');
    await expect(canvas).toBeVisible({ timeout: 10000 });

    // Wait a bit for game loop to start
    await page.waitForTimeout(3000);

    // Verify spawn log appeared
    const spawnLog = logs.find(log => log.includes('[Spawn] Stage:'));
    if (spawnLog) {
        console.log('SUCCESS: Spawn trigged:', spawnLog);
    } else {
        console.log('FAILURE: No spawn log found.');
        // Take screenshot if failed
        await page.screenshot({ path: 'spawn_fail.png' });
    }

    expect(spawnLog).toBeTruthy();
});
