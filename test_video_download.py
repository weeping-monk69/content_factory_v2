import os
import time
from playwright.sync_api import sync_playwright
from config.settings import settings

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=settings.CHROME_BOT_PROFILE_DIR,
        channel="chrome",
        headless=False,
        accept_downloads=True,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--test-type",  # Silences the unsupported command-line flag infobar
            "--start-maximized"
        ],
        ignore_default_args=["--enable-automation", "--no-sandbox"]
    )
    page = context.pages[0] if context.pages else context.new_page()
    page.goto("https://flow.google.com")
    page.wait_for_timeout(4000)

    # Click start creating if visible
    start_btn = page.locator("text='Start Creating'").first
    if start_btn.is_visible():
        start_btn.click()
        page.wait_for_timeout(3000)

    print("Opening video editor...")
    video_card = page.locator("[aria-label*='Open video in editor']").last
    video_card.wait_for(state="visible", timeout=15000)
    video_card.click()
    page.wait_for_timeout(3000)

    # Click Download media button
    print("Clicking 'Download media' button...")
    dl_icon = page.locator("[aria-label='Download media'], button:has-text('download')").first
    dl_icon.wait_for(state="visible", timeout=10000)
    dl_icon.click()
    page.wait_for_timeout(1500)

    print("Waiting for resolution dropdown...")
    raw_target = "storage/raw_video/test_clip.mp4"

    with page.expect_download(timeout=90000) as download_info:
        # Use a regex match for 720p to match anywhere in the button/item text
        option_720p = page.locator("button, [role='menuitem'], mat-list-item, div").filter(has_text=r"720p").last
        option_720p.wait_for(state="visible", timeout=10000)
        
        # Click with force=True so any transparent overlay doesn't block the click
        option_720p.click(force=True)

    download = download_info.value
    download.save_as(raw_target)
    print(f"\nSUCCESS! Raw video downloaded to: {raw_target}")

    context.close()