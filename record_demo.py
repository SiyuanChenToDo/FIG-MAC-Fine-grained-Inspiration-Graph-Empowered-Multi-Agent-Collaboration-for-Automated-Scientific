#!/usr/bin/env python3
"""
Playwright script to record FIG-MAC web demo video
"""

import asyncio
from playwright.async_api import async_playwright


async def record_demo():
    output_path = "/root/autodl-tmp/web_demo/static/demo_video.webm"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            record_video_dir="/root/autodl-tmp/videos/",
            record_video_size={"width": 1440, "height": 900},
        )
        page = await context.new_page()

        print("[1/6] Opening landing page...")
        await page.goto("http://localhost:8080")
        await page.wait_for_selector("#landing-page", state="visible")
        await asyncio.sleep(2)

        print("[2/6] Clicking Begin Discovery...")
        await page.click("#start-btn")
        await page.wait_for_selector("#input-page", state="visible")
        await asyncio.sleep(1)

        print("[3/6] Filling input form...")
        topic = "Bridging Multi-task Learning with Gating Mechanisms for NLP"
        await page.fill("#query-input", topic)
        # Ensure demo mode (toggle unchecked = demo)
        toggle = await page.query_selector("#mode-toggle")
        if toggle:
            is_checked = await toggle.is_checked()
            if is_checked:
                await toggle.click()
        await asyncio.sleep(1)

        print("[4/6] Starting demo workflow...")
        await page.click("#submit-btn")
        await page.wait_for_selector("#think-page", state="visible")

        # Wait for result page (workflow_complete triggers page switch)
        print("[5/6] Waiting for demo to complete (~45s)...")
        try:
            await page.wait_for_selector("#result-page.active", state="visible", timeout=120000)
        except Exception as e:
            print(f"Timeout waiting for result page: {e}")
            # Check if view-result-btn appeared
            try:
                await page.wait_for_selector("#view-result-btn", state="visible", timeout=10000)
                await page.click("#view-result-btn")
                await asyncio.sleep(2)
            except Exception:
                pass

        await asyncio.sleep(3)

        print("[6/6] Recording result page...")
        # Scroll through result sections
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(2)
        # Scroll to charts
        for _ in range(3):
            await page.evaluate("window.scrollBy(0, 400)")
            await asyncio.sleep(1.5)
        await asyncio.sleep(3)

        await context.close()
        await browser.close()

        # Playwright saves video with random filename; find and rename
        import glob, shutil, os
        video_files = glob.glob("/root/autodl-tmp/videos/*.webm")
        if video_files:
            video_files.sort(key=os.path.getmtime)
            src = video_files[-1]
            shutil.copy2(src, output_path)
            size_mb = os.path.getsize(output_path) / 1024 / 1024
            print(f"✅ Video saved: {output_path}")
            print(f"   Size: {size_mb:.1f} MB")
        else:
            print("❌ No video file found")


if __name__ == "__main__":
    asyncio.run(record_demo())
