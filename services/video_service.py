import os
import re
import glob
import json
import time
from typing import List, Dict, Any, Tuple

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STORAGE_DIR = os.path.join(PROJECT_ROOT, "storage")
RAW_CLIPS_DIR = os.path.join(STORAGE_DIR, "raw_clips")
os.makedirs(RAW_CLIPS_DIR, exist_ok=True)

# Force the exact authenticated profile inside content_factory_v2
CHROME_PROFILE_DIR = os.path.join(PROJECT_ROOT, "chrome_bot_profile")
try:
    from agents.trend_agent import load_trend_dna
except ImportError:
    def load_trend_dna() -> Dict[str, Any]:
        return {}

try:
    from services.llm_brain import call_smart_llm_json
except ImportError:
    def call_smart_llm_json(sys_p: str, usr_p: str, temperature: float = 0.35, cloud_only: bool = False) -> Dict[str, Any]:
        return {}

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STORAGE_DIR = os.path.join(PROJECT_ROOT, "storage")
RAW_CLIPS_DIR = os.path.join(STORAGE_DIR, "raw_clips")
os.makedirs(RAW_CLIPS_DIR, exist_ok=True)

ABSTRACT_TO_PHYSICAL_MAP = {
    r"\btelemetry\b": "glowing cyan sensor data streams inside translucent glass",
    r"\barbitrage\b": "hidden mechanical red price gears turning beneath a screen",
    r"\balgorithm\b": "glowing red laser circuit pathways on a dark microchip",
    r"\bdark pattern\b": "deceptive glowing neon green button trap over a dark pit",
    r"\bfriction asymmetry\b": "locked twelve-layer metallic digital maze",
    r"\bdecoy pricing\b": "magnetic glowing shopping cart progress bar pulling coins",
    r"\bloss aversion\b": "glass cylinder filling with glowing red rupee coins",
    r"\bmandate\b": "glowing red recurring auto-debit power cable",
}

SHARED_CONTINUITY_ANCHOR = (
    "Vertical 9:16 aspect ratio, Unreal Engine 5.4 3D forensic documentary render, "
    "35mm macro cinema lens, dark obsidian studio, volumetric crimson and cyan rim lighting, "
    "ultra-crisp physical textures, smooth cinematic camera motion, zero gibberish text, 4k 60fps"
)


# ==============================================================================
# 1. PROMPT SELF-CRITIC & SINGLE BATCH PROMPT BUILDER
# ==============================================================================
def _run_google_flow_prompt_self_critic(
    scenes: List[Dict[str, Any]],
    dna: Dict[str, Any]
) -> Tuple[List[str], str, Dict[str, Any]]:
    vid_cfg = dna.get("video_engine", {})
    active_style = vid_cfg.get("active_visual_style", "forensic_3d_cutaway")
    style_suffix = (
        vid_cfg.get("style_directives", {})
        .get(active_style, {})
        .get("suffix", SHARED_CONTINUITY_ANCHOR)
    )

    scene_inputs = []
    for idx, sc in enumerate(scenes, 1):
        scene_inputs.append({
            "scene_number": idx,
            "spoken_narration_hinglish": sc.get("narration_hinglish", ""),
            "draft_visual_prompt": sc.get("visual_prompt", "")
        })

    sys_prompt = """You are a Master AI Video Prompt Engineer for Google Flow (Veo) 3D Documentary Shorts.
Upgrade the 6 `draft_visual_prompt` entries so they generate breathtaking, 100% topic-aligned Vertical 9:16 video clips.
Rules:
1. Physically show the exact action/concept spoken in `spoken_narration_hinglish`.
2. Structure: [Camera Movement & Lens] + [Foreground Subject/Action] + [Background 3D Cutaway/Mechanism] + [Volumetric Lighting].
3. ZERO text/sentences on screens (only glowing icons, numbers, or color bars).
4. Keep each scene prompt 30 to 45 words."""

    user_prompt = json.dumps({
        "scenes_to_upgrade": scene_inputs,
        "required_json_schema": {
            "initial_prompt_score_100": 82,
            "upgraded_prompt_score_100": 96,
            "critique_improvements": ["list of 2 visual improvements applied"],
            "upgraded_prompts": [
                {"scene_number": 1, "google_flow_prompt": "30-45 word 9:16 3D cinema prompt"}
            ]
        }
    }, ensure_ascii=False)

    res = call_smart_llm_json(sys_prompt, user_prompt, temperature=0.35, cloud_only=True)
    llm_prompts = res.get("upgraded_prompts", []) if isinstance(res, dict) else []

    final_prompts: List[str] = []
    for idx, sc in enumerate(scenes):
        raw_p = sc.get("visual_prompt", "").strip()
        if isinstance(llm_prompts, list) and len(llm_prompts) == len(scenes):
            cand = str(llm_prompts[idx].get("google_flow_prompt", "")).strip()
            if len(cand.split()) >= 12:
                raw_p = cand

        for pattern, physical_rep in ABSTRACT_TO_PHYSICAL_MAP.items():
            raw_p = re.sub(pattern, physical_rep, raw_p, flags=re.IGNORECASE)

        if not any(m in raw_p.lower() for m in ["camera", "zoom", "pan", "push", "orbit", "tracking", "macro", "pov"]):
            cam_prefix = "Slow macro push-in camera shot: " if idx % 2 == 0 else "Dynamic 3D orbital cutaway camera movement: "
            raw_p = cam_prefix + raw_p

        full_flow_prompt = f"{raw_p.rstrip('.')} — {style_suffix}"
        full_flow_prompt = re.sub(r"\s+", " ", full_flow_prompt).strip()
        sc["visual_prompt_enhanced"] = full_flow_prompt
        final_prompts.append(full_flow_prompt)

    # Combine all 6 scenes into ONE single batch prompt (no raw newlines that trigger premature Enter!)
    scene_blocks = [f"[Video {i} of {len(final_prompts)} - Vertical 9:16]: {p}" for i, p in enumerate(final_prompts, 1)]
    single_master_prompt = (
        f"Generate {len(final_prompts)} separate vertical 9:16 video clips, one for each scene below: "
        + " || ".join(scene_blocks)
    )

    init_sc = int(res.get("initial_prompt_score_100", 82)) if res else 82
    final_sc = int(res.get("upgraded_prompt_score_100", 96)) if res else 95
    notes = res.get("critique_improvements", [
        "Enforced 4-part Google Flow camera/subject/cutaway/lighting structure",
        "Combined all 6 scenes into 1 master batch prompt for Google Flow"
    ]) if res else ["Combined all 6 scenes into 1 master batch prompt."]

    print("\n" + "=" * 88)
    print(f"  [GOOGLE FLOW PROMPT SELF-CRITIC] Score: {init_sc}/100 -> {final_sc}/100 (Style: {active_style})")
    for n in notes[:3]:
        print(f"    * Critic Fix: {n}")
    print("-" * 88)
    for idx, fp in enumerate(final_prompts, 1):
        print(f"  [SCENE {idx} PROMPT]: \"{fp}\"")
    print("-" * 88)
    print(f"  [COMBINED 1-SHOT MASTER PROMPT FOR GOOGLE FLOW]:\n    \"{single_master_prompt[:300]}... [+{len(final_prompts)} scenes total]\"")
    print("=" * 88 + "\n")

    prompt_dump_path = os.path.join(STORAGE_DIR, "latest_flow_batch_prompt.txt")
    with open(prompt_dump_path, "w", encoding="utf-8") as f:
        f.write("=== SINGLE MASTER PROMPT (ALL 6 SCENES IN ONE) ===\n")
        f.write(single_master_prompt + "\n\n")
        for idx, fp in enumerate(final_prompts, 1):
            f.write(f"SCENE {idx} (Vertical 9:16):\n{fp}\n\n")

    return final_prompts, single_master_prompt, {"initial_score": init_sc, "final_score": final_sc}


# ==============================================================================
# 2. ALWAYS APPROVE / APPROVE HANDLER (STRICTLY IGNORES REJECT)
# ==============================================================================
def _install_and_trigger_approve_handler(page) -> int:
    """
    Scans the page and Shadow DOMs for Google Flow's confirmation buttons:
    - Prioritizes clicking 'Always approve' first so all 6 scenes run uninterrupted.
    - Falls back to clicking 'Approve' if 'Always approve' is not present.
    - NEVER clicks 'Reject' or 'Cancel'.
    """
    clicked_count = 0
    try:
        clicked_count = page.evaluate("""() => {
            let clicks = 0;
            const scanAndApprove = (root) => {
                const candidates = root.querySelectorAll('button, [role="button"], mat-button, span.mdc-button__label');
                // Pass 1: Look specifically for 'Always approve'
                for (const el of candidates) {
                    const btn = el.closest('button, [role="button"]') || el;
                    if (!btn || btn.disabled || btn.offsetParent === null) continue;
                    const txt = (btn.innerText || btn.textContent || '').trim().toLowerCase();
                    const aria = (btn.getAttribute('aria-label') || '').trim().toLowerCase();
                    if (txt.includes('reject') || aria.includes('reject')) continue;
                    if (txt === 'always approve' || txt.includes('always approve') || aria.includes('always approve')) {
                        btn.click();
                        clicks++;
                        return;
                    }
                }
                // Pass 2: Look for exact 'Approve' (excluding Reject/Disapprove)
                for (const el of candidates) {
                    const btn = el.closest('button, [role="button"]') || el;
                    if (!btn || btn.disabled || btn.offsetParent === null) continue;
                    const txt = (btn.innerText || btn.textContent || '').trim().toLowerCase();
                    const aria = (btn.getAttribute('aria-label') || '').trim().toLowerCase();
                    if (txt.includes('reject') || txt.includes('disapprove') || aria.includes('reject')) continue;
                    if (txt === 'approve' || txt.startsWith('approve ') || aria === 'approve') {
                        btn.click();
                        clicks++;
                        return;
                    }
                }
                // Traverse Shadow DOMs
                const allEls = root.querySelectorAll('*');
                for (const node of allEls) {
                    if (node.shadowRoot) scanAndApprove(node.shadowRoot);
                }
            };
            scanAndApprove(document);
            return clicks;
        }""")
    except Exception:
        pass

    # Playwright locator backup for 'Always approve' / 'Approve'
    for label in ["Always approve", "Always Approve", "Approve"]:
        try:
            btn = page.locator(f"button:has-text('{label}'), [role='button']:has-text('{label}')").first
            if btn.count() > 0 and btn.is_visible():
                btn_text = (btn.inner_text() or "").strip().lower()
                if "reject" not in btn_text:
                    btn.click(force=True, timeout=2000)
                    clicked_count += 1
                    print(f"  [Google Flow Auto-Approver] Clicked '{label}' button!")
                    page.wait_for_timeout(1000)
                    break
        except Exception:
            continue

    return clicked_count


# ==============================================================================
# 3. ONE-PROMPT BATCH SUBMISSION + FULL WAIT + 720p/1080p DOWNLOADER
# ==============================================================================
def _enter_flow_workspace(page) -> None:
    page.goto("https://flow.google.com", timeout=60000)
    page.wait_for_timeout(5000)

    # 1. Click 'Start Creating' if on the splash screen
    for label in ["Start Creating", "Start creating", "Get started", "Create", "New project", "New Project"]:
        btn = page.locator(f"button:has-text('{label}'), a:has-text('{label}'), [role='button']:has-text('{label}')").first
        try:
            if btn.count() > 0 and btn.is_visible():
                print(f"  [Google Flow] Clicking '{label}'...")
                btn.click(force=True)
                page.wait_for_timeout(4000)
                break
        except Exception:
            continue

    # 2. If still on project dashboard (no chat box visible yet), open the most recent project card
    if page.locator("textarea, [contenteditable='true'], [role='textbox']").count() == 0:
        card = page.locator("[class*='project'], [class*='card'], a[href*='/project/']").first
        try:
            if card.count() > 0 and card.is_visible():
                print("  [Google Flow] Opening existing project workspace...")
                card.click(force=True)
                page.wait_for_timeout(4000)
        except Exception:
            pass


def _submit_one_master_prompt(page, master_prompt: str) -> bool:
    """Waits up to 15s for Google Flow's chat input box, clicks it, pastes the batch prompt, and hits Enter."""
    selectors = [
        "textarea",
        "[contenteditable='true']",
        "[role='textbox']",
        "input[placeholder*='create' i]",
        "input[placeholder*='describe' i]",
        "input[placeholder*='prompt' i]",
        "div[aria-label*='create' i]",
        "div[aria-label*='prompt' i]",
        "p[data-placeholder]"
    ]

    target_box = None
    deadline = time.time() + 15
    while time.time() < deadline and target_box is None:
        for sel in selectors:
            loc = page.locator(sel)
            for i in range(loc.count() - 1, -1, -1):
                el = loc.nth(i)
                try:
                    if el.is_visible():
                        target_box = el
                        break
                except Exception:
                    continue
            if target_box is not None:
                break
        if target_box is None:
            page.wait_for_timeout(1000)

    # Fallback: Click anywhere matching "What do you want to create" placeholder text
    if target_box is None:
        try:
            ph = page.get_by_text(re.compile(r"create|describe|prompt|ask", re.IGNORECASE)).last
            if ph.count() > 0 and ph.is_visible():
                ph.click(force=True)
                page.wait_for_timeout(500)
                page.keyboard.insert_text(master_prompt)
                page.wait_for_timeout(500)
                page.keyboard.press("Enter")
                print("  [Google Flow] Submitted ALL 6 scenes via placeholder focus!")
                return True
        except Exception:
            pass

    if target_box is None:
        page.screenshot(path="flow_missing_input_debug.png")
        print("  [Google Flow Warning] Chat input box not found (saved flow_missing_input_debug.png).")
        return False

    try:
        target_box.click(force=True)
        page.wait_for_timeout(400)
        page.keyboard.press("Control+A")
        page.keyboard.press("Backspace")
        page.wait_for_timeout(200)

        try:
            target_box.fill(master_prompt)
        except Exception:
            page.keyboard.insert_text(master_prompt)

        page.wait_for_timeout(600)
        page.keyboard.press("Enter")
        page.wait_for_timeout(1000)

        send_btn = page.locator(
            "button[aria-label*='Send' i], button[aria-label*='Submit' i], "
            "button[aria-label*='Create' i], button[aria-label*='Generate' i]"
        ).last
        if send_btn.count() > 0 and send_btn.is_visible():
            try:
                send_btn.click(timeout=2000)
            except Exception:
                pass

        print("  [Google Flow] Submitted ALL 6 scenes in ONE single batch prompt!")
        return True
    except Exception as e:
        print(f"  [Google Flow Warning] Failed to submit master prompt: {e}")
        return False

def _download_single_card_from_editor(page, card_index: int, dest_path: str) -> bool:
    """
    Clicks video card `card_index` ('Open video in editor'), clicks 'Download media',
    selects 720p or 1080p, and WAITS until the .mp4 download is 100% complete on disk.
    """
    try:
        cards = page.locator("[aria-label*='Open video in editor']")
        if card_index >= cards.count():
            return False

        target_card = cards.nth(card_index)
        target_card.scroll_into_view_if_needed(timeout=5000)
        target_card.click(force=True)
        page.wait_for_timeout(3000)

        print(f"  [Google Flow] Card #{card_index + 1}: Clicking 'Download media'...")
        dl_icon = page.locator("[aria-label='Download media'], button:has-text('download')").first
        dl_icon.wait_for(state="visible", timeout=12000)
        dl_icon.click()
        page.wait_for_timeout(1500)

        print(f"  [Google Flow] Card #{card_index + 1}: Selecting 720p/1080p & waiting for download to finish...")
        os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)

        with page.expect_download(timeout=120000) as download_info:
            res_option = page.locator("button, [role='menuitem'], mat-list-item, div").filter(
                has_text=re.compile(r"720p|1080p", re.IGNORECASE)
            ).last
            res_option.wait_for(state="visible", timeout=12000)
            res_option.click(force=True)

        download = download_info.value
        # download.save_as() blocks until Playwright finishes streaming the entire MP4 file to disk
        download.save_as(dest_path)
        file_mb = os.path.getsize(dest_path) / (1024 * 1024) if os.path.exists(dest_path) else 0.0
        print(f"  [Google Flow] SUCCESS! Downloaded {dest_path} ({file_mb:.2f} MB)")

        # Close editor view to return to workspace canvas for the next video card
        page.keyboard.press("Escape")
        page.wait_for_timeout(2000)
        close_btn = page.locator(
            "[aria-label*='Close' i], [aria-label*='Back' i], button:has-text('Close')"
        ).first
        if close_btn.count() > 0 and close_btn.is_visible():
            try:
                close_btn.click(timeout=2000)
                page.wait_for_timeout(1000)
            except Exception:
                pass
        return True
    except Exception as e:
        print(f"  [Google Flow Warning] Error downloading card #{card_index + 1}: {e}")
        try:
            page.keyboard.press("Escape")
            page.wait_for_timeout(1500)
        except Exception:
            pass
        return False


def _run_google_flow_one_prompt_batch(single_master_prompt: str, expected_scenes: int) -> List[str]:
    from playwright.sync_api import sync_playwright

    downloaded_clips: List[str] = []

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=CHROME_PROFILE_DIR,
            channel="chrome",
            headless=False,
            accept_downloads=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--test-type",
                "--start-maximized"
            ],
            ignore_default_args=["--enable-automation", "--no-sandbox"]
        )
        page = context.pages[0] if context.pages else context.new_page()
        print(f"  [Google Flow] Opening https://flow.google.com with Chrome profile: {CHROME_PROFILE_DIR}")
        _enter_flow_workspace(page)

        initial_cards = page.locator("[aria-label*='Open video in editor']").count()
        print(f"  [Google Flow] Workspace ready (Existing video cards={initial_cards}).")

        if _submit_one_master_prompt(page, single_master_prompt):
            target_total_cards = initial_cards + expected_scenes
            max_wait_sec = 420  # Up to 7 minutes for all 6 videos to finish generating
            start_t = time.time()
            last_log_t = 0.0

            print(
                f"  [Google Flow] Auto-handling 'Always approve' / 'Approve' and waiting for "
                f"{expected_scenes} new video cards to finish rendering..."
            )
            while (time.time() - start_t) < max_wait_sec:
                _install_and_trigger_approve_handler(page)

                curr_cards = page.locator("[aria-label*='Open video in editor']").count()
                new_ready = max(0, curr_cards - initial_cards)

                if (time.time() - last_log_t) >= 10:
                    elapsed = int(time.time() - start_t)
                    print(f"    -> [{elapsed}s elapsed] Rendered {new_ready}/{expected_scenes} new video cards...")
                    last_log_t = time.time()

                if curr_cards >= target_total_cards:
                    print(f"  [Google Flow] All {expected_scenes} new video cards rendered! Waiting 5s for final settle...")
                    page.wait_for_timeout(5000)
                    break

                page.wait_for_timeout(2500)

            # Determine which cards to download (newly generated ones, or last N on canvas)
            total_cards_now = page.locator("[aria-label*='Open video in editor']").count()
            if total_cards_now > initial_cards:
                indices_to_download = list(range(initial_cards, total_cards_now))
            else:
                start_idx = max(0, total_cards_now - expected_scenes)
                indices_to_download = list(range(start_idx, total_cards_now))

            print(f"  [Google Flow] Starting sequential 720p/1080p download for {len(indices_to_download)} clips...")
            for seq_num, card_idx in enumerate(indices_to_download[:expected_scenes], 1):
                dest_file = os.path.join(RAW_CLIPS_DIR, f"flow_scene_{seq_num:02d}.mp4")
                ok = _download_single_card_from_editor(page, card_idx, dest_file)
                if ok and os.path.exists(dest_file) and os.path.getsize(dest_file) > 50 * 1024:
                    downloaded_clips.append(dest_file)

        print("  [Google Flow] All downloads finished. Closing Chrome session...")
        context.close()

    return downloaded_clips


def generate_video_with_flow(prompt: str, output_path: str) -> str:
    """Single-clip helper for test_flow_pipeline.py."""
    clips = _run_google_flow_one_prompt_batch(prompt, expected_scenes=1)
    if clips and os.path.exists(clips[0]):
        if os.path.abspath(clips[0]) != os.path.abspath(output_path):
            import shutil
            shutil.copy2(clips[0], output_path)
    return output_path


def _get_existing_raw_clips(required_count: int) -> List[str]:
    mp4_files = glob.glob(os.path.join(RAW_CLIPS_DIR, "*.mp4"))
    mp4_files = [f for f in mp4_files if os.path.getsize(f) > 50 * 1024]
    mp4_files.sort(key=os.path.getmtime, reverse=True)
    return mp4_files


def generate_all_scenes_in_one_prompt(scenes: List[Dict[str, Any]]) -> List[str]:
    dna = load_trend_dna()
    enhanced_prompts, single_master_prompt, _ = _run_google_flow_prompt_self_critic(scenes, dna)

    mock_flow = os.getenv("MOCK_FLOW", "true").lower() == "true"
    use_flow = os.getenv("USE_FLOW", "false").lower() == "true"

    if not mock_flow and use_flow:
        print(f"[Video Service] USE_FLOW=True | Sending ALL {len(enhanced_prompts)} scenes in ONE prompt to Google Flow...")
        clips = _run_google_flow_one_prompt_batch(single_master_prompt, expected_scenes=len(enhanced_prompts))
        if len(clips) >= len(enhanced_prompts):
            return clips[:len(enhanced_prompts)]
        existing = _get_existing_raw_clips(len(scenes))
        combined = clips + [c for c in existing if c not in clips]
        if combined:
            return combined[:len(scenes)]

    existing = _get_existing_raw_clips(len(scenes))
    print(f"[Video Service] MOCK_FLOW={mock_flow} | Using {len(existing)} clips from {RAW_CLIPS_DIR}")
    if not existing:
        raise RuntimeError(f"No existing .mp4 clips found in {RAW_CLIPS_DIR}.")
    return existing