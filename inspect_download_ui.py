from playwright.sync_api import sync_playwright
from config.settings import settings

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=settings.CHROME_BOT_PROFILE_DIR,
        channel="chrome",
        headless=False
    )
    page = context.pages[0] if context.pages else context.new_page()
    page.goto("https://flow.google.com")
    page.wait_for_timeout(5000)

    # Click start creating if present
    start_btn = page.locator("text='Start Creating'").first
    if start_btn.is_visible():
        start_btn.click()
        page.wait_for_timeout(3000)

    # Find media cards or video elements in the workspace
    print("\nScanning for media cards/elements...")
    cards = page.locator("video, img, [class*='media-card'], [class*='asset-card'], [class*='canvas-node']").all()
    print(f"Found {len(cards)} candidate media elements.")

    # Hover over the last card to expose action bars
    for i, c in enumerate(cards):
        try:
            if c.is_visible():
                print(f"Hovering over visible card [{i}]...")
                c.hover()
                page.wait_for_timeout(1000)
                break
        except Exception:
            pass

    page.screenshot(path="card_hover_state.png")
    print("Saved 'card_hover_state.png'")

    # Dump all visible buttons and icons now that hover state is active
    print("\n--- VISIBLE BUTTONS & ICONS POST-HOVER ---")
    buttons = page.locator("button, [role='button'], a[download]").all()
    for idx, b in enumerate(buttons):
        try:
            if b.is_visible():
                txt = b.inner_text().strip().replace("\n", " ")
                aria = b.get_attribute("aria-label") or ""
                title = b.get_attribute("title") or ""
                print(f"[{idx}] Text: '{txt}' | Aria: '{aria}' | Title: '{title}'")
        except Exception:
            pass

    input("\nPress ENTER in PowerShell to finish inspection...")
    context.close()