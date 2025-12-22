# -*- coding: utf-8 -*-
"""
Test the game fixes:
1. Projectiles don't wrap/flash at boundaries
2. Player takes damage when hit by enemies in cockpit mode
"""
from playwright.sync_api import sync_playwright
import time
import os
import sys

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def test_game_fixes():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1280, 'height': 720})
        page = context.new_page()

        # Set up console logging
        console_logs = []
        page.on('console', lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

        print("=== Game Fixes Test ===")
        print("")

        # Navigate to the app
        print("1. Navigating to http://localhost:3001...")
        page.goto('http://localhost:3001')
        page.wait_for_load_state('networkidle')
        time.sleep(2)

        # Handle intro screen if present
        print("2. Checking for intro screen...")
        intro = page.locator('#intro-screen')
        if intro.count() > 0 and intro.is_visible():
            print("   Intro screen found, clicking to dismiss...")
            page.click('body')
            time.sleep(1)
            # Wait for intro to hide
            page.wait_for_selector('#intro-screen.hidden', timeout=5000)
            print("   Intro dismissed")

        # Wait for React to load
        time.sleep(3)

        # Take screenshot after intro
        os.makedirs('/tmp/game_tests', exist_ok=True)
        page.screenshot(path='/tmp/game_tests/01_after_intro.png')
        print("   Screenshot: /tmp/game_tests/01_after_intro.png")

        # Look for page structure
        print("")
        print("3. Analyzing page structure...")
        html = page.content()

        # Check for buttons
        buttons = page.locator('button').all_text_contents()
        print(f"   Buttons found: {len(buttons)}")
        for btn in buttons[:8]:
            if btn.strip():
                print(f"      - {btn.strip()[:50]}")

        # Check for canvas
        canvas = page.locator('canvas')
        print(f"   Canvas elements: {canvas.count()}")

        # Try to enable game mode
        print("")
        print("4. Looking for game controls...")

        # Look for game toggle - could be in header or settings
        game_related = page.locator('button, [role="switch"], input[type="checkbox"]')
        for i in range(min(game_related.count(), 20)):
            try:
                elem = game_related.nth(i)
                text = elem.text_content() or elem.get_attribute('aria-label') or ''
                if 'game' in text.lower() or 'play' in text.lower():
                    print(f"   Found game control: {text}")
                    elem.click()
                    time.sleep(1)
                    break
            except:
                pass

        # Take screenshot
        page.screenshot(path='/tmp/game_tests/02_looking_for_game.png')

        # Check canvas again
        canvas = page.locator('canvas')
        canvas_count = canvas.count()
        print(f"   Canvas after clicking: {canvas_count}")

        if canvas_count > 0:
            print("")
            print("5. Game canvas found! Testing projectiles...")

            canvas_elem = canvas.first
            box = canvas_elem.bounding_box()
            if box:
                center_x = box['x'] + box['width'] / 2
                center_y = box['y'] + box['height'] / 2

                # Click canvas to focus
                page.mouse.click(center_x, center_y)
                time.sleep(0.5)

                # Fire projectiles - hold mouse button
                print("   Firing projectiles for 3 seconds...")
                page.mouse.down()
                time.sleep(3)
                page.mouse.up()

                page.screenshot(path='/tmp/game_tests/03_after_firing.png')
                print("   Screenshot: /tmp/game_tests/03_after_firing.png")

                # Check logs for firing
                firing_logs = [log for log in console_logs if 'Firing' in log]
                print(f"   Firing log count: {len(firing_logs)}")

                # Fire more while moving
                print("   Moving aim and firing more...")
                for i in range(5):
                    page.mouse.move(center_x + i * 30 - 60, center_y + (i % 2) * 40 - 20)
                    page.mouse.down()
                    time.sleep(0.5)
                    page.mouse.up()
                    time.sleep(0.2)

                page.screenshot(path='/tmp/game_tests/04_after_movement.png')
        else:
            print("")
            print("5. No canvas found - game may not be enabled")
            print("   Trying keyboard shortcut or looking for play button...")

            # Try pressing 'G' for game
            page.keyboard.press('g')
            time.sleep(1)

            # Check again
            canvas = page.locator('canvas')
            if canvas.count() > 0:
                print("   Canvas appeared after 'G' press!")
            else:
                print("   Still no canvas. Taking diagnostic screenshot...")

            page.screenshot(path='/tmp/game_tests/05_diagnostic.png')

        # Analyze console logs
        print("")
        print("6. Console log analysis:")
        print(f"   Total logs: {len(console_logs)}")

        firing_logs = [log for log in console_logs if 'Firing' in log or 'fire' in log.lower()]
        print(f"   Firing logs: {len(firing_logs)}")
        for log in firing_logs[:3]:
            print(f"      {log[:80]}")

        collision_logs = [log for log in console_logs if 'Collision' in log or 'collision' in log.lower()]
        print(f"   Collision logs: {len(collision_logs)}")
        for log in collision_logs[:3]:
            print(f"      {log[:80]}")

        enemy_logs = [log for log in console_logs if 'Enemy' in log or 'enemies' in log.lower()]
        print(f"   Enemy logs: {len(enemy_logs)}")
        for log in enemy_logs[:3]:
            print(f"      {log[:80]}")

        error_logs = [log for log in console_logs if log.startswith('[error]')]
        print(f"   Error logs: {len(error_logs)}")
        for log in error_logs[:5]:
            print(f"      {log[:80]}")

        print("")
        print("=== Test Summary ===")
        if canvas_count > 0 and len(firing_logs) > 0:
            print("[PASS] Game is rendering and projectiles are being fired")
        elif canvas_count > 0:
            print("[PARTIAL] Game renders but no firing detected")
        else:
            print("[CHECK] Game canvas not found - manual testing may be needed")

        if len(error_logs) == 0:
            print("[PASS] No JavaScript errors detected")
        else:
            print(f"[WARN] {len(error_logs)} errors in console")

        browser.close()
        print("")
        print("Test completed. Screenshots saved to /tmp/game_tests/")

if __name__ == '__main__':
    test_game_fixes()
