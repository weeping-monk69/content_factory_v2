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

    # Click 'Start Creating' if present
    start_btn = page.locator("text='Start Creating'").first
    if start_btn.is_visible():
        start_btn.click()
        page.wait_for_timeout(3000)

    # Inspect all elements matching placeholder or text
    selectors = [
        "input",
        "textarea",
        "[contenteditable]",
        "[role='textbox']",
        "p",
        "div"
    ]
    print("\n--- MATCHING ELEMENTS ---")
    for s in selectors:
        for el in page.locator(s).all():
            try:
                txt = el.inner_text().strip()
                ph = el.get_attribute("placeholder") or ""
                aria = el.get_attribute("aria-label") or ""
                if "create" in (txt + ph + aria).lower():
                    tag = el.evaluate("e => e.tagName.toLowerCase()")
                    cls = el.get_attribute("class") or ""
                    print(f"Tag: <{tag}> | Placeholder: '{ph}' | Aria: '{aria}' | Class: '{cls}' | Text: '{txt}'")
            except Exception:
                pass

    context.close()