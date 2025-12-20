import { test, expect } from '@playwright/test';

test('game loads and enters desktop mode on local dev', async ({ page }) => {
    page.on('console', msg => console.log('PAGE LOG:', msg.text()));
    page.on('pageerror', err => console.log('PAGE ERROR:', err.message));

    // Use 5173
    await page.goto('http://localhost:5173');

    const canvas = page.locator('canvas');
    await expect(canvas).toBeVisible({ timeout: 10000 });
});
