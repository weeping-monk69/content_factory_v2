from playwright.sync_api import sync_playwright
from config.settings import settings

def inspect_flow():
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=settings.CHROME_BOT_PROFILE_DIR,
            channel="chrome",
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--start-maximized"],
            ignore_default_args=["--enable-automation"]
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(settings.AI_PRO_FLOW_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(6000)

        # Save screenshot to check exactly what rendered
        screenshot_path = "flow_page_state.png"
        page.screenshot(path=screenshot_path)
        print(f"Saved page screenshot to: {screenshot_path}")

        # Scan and print all visible textareas, inputs, and contenteditable elements
        elements = page.locator("textarea, input, [contenteditable='true'], [role='textbox']").all()
        print(f"\nFound {len(elements)} candidate input elements:")
        for idx, el in enumerate(elements):
            try:
                visible = el.is_visible()
                tag = el.evaluate("e => e.tagName.toLowerCase()")
                aria = el.get_attribute("aria-label") or ""
                placeholder = el.get_attribute("placeholder") or ""
                el_id = el.get_attribute("id") or ""
                classes = el.get_attribute("class") or ""
                print(f"[{idx}] Tag: {tag} | Visible: {visible} | ID: {el_id} | Aria: '{aria}' | Placeholder: '{placeholder}' | Classes: '{classes[:40]}'")
            except Exception as e:
                print(f"[{idx}] Error reading element: {e}")

        context.close()

if __name__ == "__main__":
    inspect_flow()