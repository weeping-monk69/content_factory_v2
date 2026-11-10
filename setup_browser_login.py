from playwright.sync_api import sync_playwright
from config.settings import settings

def launch_session():
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=settings.CHROME_BOT_PROFILE_DIR,
            channel="chrome",
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized"
            ],
            ignore_default_args=["--enable-automation"]
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://labs.google/fx/tools/flow")
        
        print("Browser launched and waiting.")
        input("Press ENTER in this terminal ONLY after you have verified/logged into your account...\n")
        
        print("Saving profile state and exiting cleanly.")
        try:
            context.close()
        except Exception:
            pass

if __name__ == "__main__":
    launch_session()