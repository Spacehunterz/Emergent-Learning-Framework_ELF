# -*- coding: utf-8 -*-
"""
Visual test for game fixes - runs in headed mode for manual verification
"""
from playwright.sync_api import sync_playwright
import time
import os
import sys

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def test_game_visual():
    with sync_playwright() as p:
        # Launch in headed mode for visual verification
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={'width': 1280, 'height': 720})
        page = context.new_page()

        # Set up console logging
        console_logs = []
        page.on('console', lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

        print("=== Game Visual Test ===")
        print("")

        # Navigate to the app
        print("1. Navigating to http://localhost:3001...")
        page.goto('http://localhost:3001')
        page.wait_for_load_state('networkidle')
        time.sleep(3)

        # Get page HTML to understand structure
        print("2. Analyzing page structure...")
        buttons = page.locator('button').all_text_contents()
        print(f"   Found buttons: {buttons[:10]}")  # First 10

        links = page.locator('a').all_text_contents()
        print(f"   Found links: {links[:10]}")

        # Look for any toggle or game enable
        print("")
        print("3. Looking for game toggle...")

        # Try different selectors for game toggle
        selectors_to_try = [
            'button:has-text("Game")',
            '[data-testid*="game"]',
            'input[type="checkbox"]',
            '.toggle',
            'button:has-text("Enable")',
            'button:has-text("Play")',
            'button:has-text("Start")',
        ]

        for selector in selectors_to_try:
            try:
                elem = page.locator(selector).first
                if elem.is_visible(timeout=500):
                    print(f"   Found: {selector}")
                    elem.click()
                    time.sleep(1)
            except:
                pass

        # Take screenshot
        os.makedirs('/tmp/game_tests', exist_ok=True)
        page.screenshot(path='/tmp/game_tests/visual_test.png')
        print("   Screenshot: /tmp/game_tests/visual_test.png")

        # Check for canvas now
        print("")
        print("4. Checking for canvas...")
        canvas = page.locator('canvas')
        canvas_count = canvas.count()
        print(f"   Canvas elements: {canvas_count}")

        if canvas_count > 0:
            print("   Game canvas found!")

            # Get canvas bounding box
            canvas_elem = canvas.first
            box = canvas_elem.bounding_box()
            if box:
                print(f"   Canvas size: {box['width']}x{box['height']}")

                center_x = box['x'] + box['width'] / 2
                center_y = box['y'] + box['height'] / 2

                # Click to focus
                print("")
                print("5. Clicking canvas to focus...")
                page.mouse.click(center_x, center_y)
                time.sleep(1)

                # Fire projectiles
                print("6. Firing projectiles (hold mouse for 3 seconds)...")
                page.mouse.down()
                time.sleep(3)
                page.mouse.up()

                page.screenshot(path='/tmp/game_tests/after_firing.png')
                print("   Screenshot: /tmp/game_tests/after_firing.png")

                # Move mouse and fire more
                print("7. Moving aim and firing more...")
                page.mouse.move(center_x + 100, center_y - 50)
                page.mouse.down()
                time.sleep(2)
                page.mouse.up()

                page.screenshot(path='/tmp/game_tests/after_moving.png')

        # Check console for firing logs
        print("")
        print("8. Console logs analysis:")
        firing_logs = [log for log in console_logs if 'Firing' in log or 'SpaceShooter' in log]
        print(f"   Firing logs: {len(firing_logs)}")
        for log in firing_logs[:5]:
            print(f"      {log[:100]}")

        hit_logs = [log for log in console_logs if 'hit' in log.lower() or 'damage' in log.lower()]
        print(f"   Hit/damage logs: {len(hit_logs)}")
        for log in hit_logs[:5]:
            print(f"      {log[:100]}")

        error_logs = [log for log in console_logs if log.startswith('[error]')]
        print(f"   Error logs: {len(error_logs)}")
        for log in error_logs[:5]:
            print(f"      {log[:100]}")

        print("")
        print("=== Test Complete ===")
        print("Browser will stay open for 10 seconds for manual inspection...")
        time.sleep(10)

        browser.close()

if __name__ == '__main__':
    test_game_visual()
