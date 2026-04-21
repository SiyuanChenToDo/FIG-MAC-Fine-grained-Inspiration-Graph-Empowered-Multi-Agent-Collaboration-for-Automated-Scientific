#!/usr/bin/env python3
"""Capture clean screenshots of the English web demo for README"""

import asyncio
from playwright.async_api import async_playwright


async def capture():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})

        # 1. Landing page
        print("[1/3] Capturing landing page...")
        await page.goto("http://localhost:8080")
        await page.wait_for_selector("#landing-page", state="visible")
        await asyncio.sleep(1)
        await page.screenshot(path="/root/autodl-tmp/assets/screenshot_landing.png", full_page=False)

        # 2. Think page (agent round-table)
        print("[2/3] Capturing think page...")
        await page.click("#start-btn")
        await page.wait_for_selector("#input-page", state="visible")
        await page.fill("#query-input", "Multi-task learning with gating mechanisms")
        # Ensure demo mode
        toggle = await page.query_selector("#mode-toggle")
        if toggle and await toggle.is_checked():
            await toggle.click()
        await page.click("#submit-btn")
        await page.wait_for_selector("#think-page", state="visible")
        # Wait for agents to appear
        await asyncio.sleep(8)
        await page.screenshot(path="/root/autodl-tmp/assets/screenshot_think.png", full_page=False)

        # 3. Result page
        print("[3/3] Capturing result page...")
        # Click view result button or wait for auto navigation
        try:
            btn = await page.query_selector("#view-result-btn")
            if btn and await btn.is_visible():
                await btn.click()
        except Exception:
            pass
        # Wait for result page
        for _ in range(30):
            is_active = await page.evaluate("() => document.getElementById('result-page').classList.contains('active')")
            if is_active:
                break
            await asyncio.sleep(1)
        await asyncio.sleep(2)
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(0.5)
        await page.screenshot(path="/root/autodl-tmp/assets/screenshot_result.png", full_page=False)

        await browser.close()
        print("✅ All screenshots captured")


if __name__ == "__main__":
    asyncio.run(capture())
