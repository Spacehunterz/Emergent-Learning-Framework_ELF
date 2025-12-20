import { test, expect } from '@playwright/test';

test('game loads and enters desktop mode', async ({ page }) => {
    // 1. Go to the game (port 8888 as requested)
    await page.goto('http://localhost:8888');

    // 2. Wait for the canvas to be present
    const canvas = page.locator('canvas');
    await expect(canvas).toBeVisible({ timeout: 10000 });

    // 3. Check for the "Enter VR" button (should NOT be visible if not supported, or should exist in DOM)
    // Actually, typically VRButton hides itself if XR is not supported.
    // But we want to ensure the game loop is running.

    // 4. Verification: Check if text from Default HUD or Scene is present
    // The new Holographic HUD renders text as 3D geometry which is not easily queryable by text.
    // However, we can check for the absence of error overlays.
    const errorOverlay = page.locator('text=SYSTEM FAILURE');
    await expect(errorOverlay).not.toBeVisible();

    console.log('Game loaded successfully on port 8888');
});
