import { test, expect } from '@playwright/test';

test('Game Mode and Cursors', async ({ page }) => {
    // 1. Go to Dashboard
    await page.goto('http://localhost:5173');

    // 2. Open Game Menu (CMD+K or Button - finding button is safer)
    // Assuming there's a menu button or keybinding. Let's try the keybinding 'k' with meta
    await page.keyboard.press('Control+k');

    // 3. Verify Menu Opens
    await expect(page.locator('text=Cosmic Armory')).toBeVisible();

    // 4. Test Cursor Selection
    await page.click('text=Ships');
    await page.click('text=Surveillance Drone');
    await expect(page.locator('text=EQUIPPED')).toBeVisible();

    // 5. Enable Game Mode
    await page.click('text=GAME MODE: OFF');
    await expect(page.locator('text=GAME MODE: ON')).toBeVisible();

    // 6. Close Menu
    await page.keyboard.press('Escape');

    // 7. Verify Game Canvas presence
    // The canvas is in GameScene, usually a <canvas> element
    await expect(page.locator('canvas')).toBeVisible();

    // 8. Wait for Wave 1 (WaveManager starts after 2s)
    await page.waitForTimeout(3000);

    // 9. Take Screenshot of Game Action
    await page.screenshot({ path: 'game_mode_active.png' });
});
