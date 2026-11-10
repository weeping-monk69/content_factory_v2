import os
import json
import argparse
import subprocess
from datetime import datetime
from typing import Dict, Any, List

try:
    from services.llm_brain import call_smart_llm_json
except ImportError:
    def call_smart_llm_json(sys_p: str, usr_p: str, temperature: float = 0.35, cloud_only: bool = False) -> Dict[str, Any]:
        return {}

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STORAGE_DIR = os.path.join(PROJECT_ROOT, "storage")
TREND_DNA_PATH = os.path.join(STORAGE_DIR, "trend_dna.json")
TELEMETRY_LOG_PATH = os.path.join(STORAGE_DIR, "telemetry_matrix_log.json")

DEFAULT_TREND_DNA: Dict[str, Any] = {
    "version": "v2.5-self-evolving-params",
    "last_updated": datetime.now().isoformat(),
    "topic_engine": {
        "niche_queries": [
            "dark psychology tricks hindi shorts",
            "upi bank scam exposed hindi shorts",
            "hidden charges apps exposed hindi shorts",
            "smartphone privacy settings hindi shorts",
            "consumer fraud india exposed shorts"
        ],
        "active_collision_vectors": [
            {"id": "authority_panic", "weight": 1.35, "description": "Telecom/banking command or fake authority panic exploit"},
            {"id": "hardware_telemetry", "weight": 1.30, "description": "Phone sensors/battery/clipboard silently betraying the user"},
            {"id": "hidden_arbitrage", "weight": 1.25, "description": "Decoy pricing, zero-cost EMI GST math, or cart threshold traps"},
            {"id": "friction_asymmetry", "weight": 1.20, "description": "1-click entry vs 12-screen Roach Motel exit UI traps"}
        ]
    },
    "script_engine": {
        "target_word_bounds": [118, 134],
        "target_duration_bounds_sec": [46.0, 54.0],
        "max_hook_words": 19,
        "banned_openers": ["क्या आप जानते हैं", "नमस्कार दोस्तों", "आज हम बात करेंगे", "हेल्लो दोस्तों"],
        "hook_templates": [
            {
                "id": "accusatory_action_trap",
                "template": "जब {trigger}, तभी बैकग्राउंड में '{focus}' का जाल एक्टिव हो जाता है!",
                "weight": 1.35
            },
            {
                "id": "illusion_reversal_shock",
                "template": "अगर {trigger}, तो रुकिए! आपके फोन में '{focus}' चालू हो चुका है!",
                "weight": 1.25
            },
            {
                "id": "silent_sensor_betrayal",
                "template": "सावधान! जैसे ही {trigger}, तुरंत '{focus}' का खामोश खेल शुरू होता है!",
                "weight": 1.20
            }
        ],
        "mid_video_twist_templates": [
            {
                "id": "escalation_reveal",
                "prefix": "असली खेल यह है—",
                "required_markers": ["असली खेल", "सबसे खतरनाक", "यही नहीं"],
                "weight": 1.30
            }
        ]
    },
    "audio_engine": {
        "active_cadence_profile": "high_tension_documentary",
        "cadence_profiles": {
            "high_tension_documentary": {
                "base_rate_pct": 8,
                "mid_clause_pause_ms": 240,
                "inter_scene_breath_ms": 220,
                "max_pause_dead_air_ms": 240,
                "weight": 1.35
            }
        }
    },
    "video_engine": {
        "active_visual_style": "forensic_3d_cutaway",
        "style_directives": {
            "forensic_3d_cutaway": {
                "suffix": "Vertical 9:16, Unreal Engine 5.4 3D forensic cutaway, dark obsidian studio, glowing crimson and cyan telemetry highlights, macro 35mm depth of field, smooth camera movement, zero gibberish text, 4k",
                "weight": 1.35
            }
        }
    },
    "assembly_engine": {
        "active_edit_profile": "viral_center_yellow",
        "edit_profiles": {
            "viral_center_yellow": {
                "recommended_visual_cuts": 6,
                "alternate_zoom_scale": "1188:2112",
                "font_size": 15,
                "primary_colour_ass": "&H0000FFFF",
                "margin_v": 58,
                "subtitle_burst_words": 4,
                "weight": 1.35
            }
        }
    },
    "seo_engine": {
        "active_title_template": "warning_bracket",
        "title_templates": [
            {"id": "warning_bracket", "pattern": "{topic} ⚠️ [सावधान] #shorts #darkpsychology", "weight": 1.30}
        ]
    },
    "dynamic_discovered_parameters": [
        {
            "param_id": "numeric_shock_specificity",
            "name": "Forensic Numeric Specificity",
            "rule": "Scene 3 must anchor the claim with an exact odd percentage or Rupee figure (e.g., 38%, ₹1,140) rather than vague words like 'बहुत ज़्यादा'.",
            "target_benchmark": "100% of scripts contain >=1 exact figure",
            "discovered_from": "1M+ Viral Shorts Baseline"
        },
        {
            "param_id": "micro_action_defense_clarity",
            "name": "3-Second Actionable Defense Toggle",
            "rule": "Scene 5 must name the exact phone menu or financial action (e.g., 'UPI AutoPay Pause', 'Clipboard Alert Toggle') the viewer can do in 10 seconds.",
            "target_benchmark": "Concrete setting named in Scene 5",
            "discovered_from": "1M+ Viral Shorts Baseline"
        },
        {
            "param_id": "foreground_background_visual_contrast",
            "name": "Dual-Layer Visual Depth",
            "rule": "Each Google Flow prompt must pair a human hand/phone in the foreground with a 3D X-ray mechanism in the background.",
            "target_benchmark": ">=90/100 Prompt Critic Score",
            "discovered_from": "1M+ Viral Shorts Baseline"
        }
    ],
    "viral_pattern_insights": []
}


def load_trend_dna() -> Dict[str, Any]:
    os.makedirs(STORAGE_DIR, exist_ok=True)
    if not os.path.exists(TREND_DNA_PATH):
        save_trend_dna(DEFAULT_TREND_DNA)
        return json.loads(json.dumps(DEFAULT_TREND_DNA))
    try:
        with open(TREND_DNA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            aud = data.setdefault("audio_engine", {}).setdefault("cadence_profiles", {}).setdefault("high_tension_documentary", {})
            aud["mid_clause_pause_ms"] = int(aud.get("mid_clause_pause_ms", 240))
            if aud["mid_clause_pause_ms"] < 180:
                aud["mid_clause_pause_ms"] = 240
            aud["inter_scene_breath_ms"] = int(aud.get("inter_scene_breath_ms", 220))
            if aud["inter_scene_breath_ms"] < 160:
                aud["inter_scene_breath_ms"] = 220
            data.setdefault("dynamic_discovered_parameters", DEFAULT_TREND_DNA["dynamic_discovered_parameters"])
            return data
    except Exception:
        return json.loads(json.dumps(DEFAULT_TREND_DNA))


def save_trend_dna(dna: Dict[str, Any]) -> None:
    os.makedirs(STORAGE_DIR, exist_ok=True)
    dna["last_updated"] = datetime.now().isoformat()
    with open(TREND_DNA_PATH, "w", encoding="utf-8") as f:
        json.dump(dna, f, ensure_ascii=False, indent=2)


def _scrape_viral_shorts_metadata(queries: List[str], per_query: int = 5) -> List[Dict[str, Any]]:
    collected: List[Dict[str, Any]] = []
    for q in queries:
        cmd = [
            "yt-dlp",
            f"ytsearch{per_query}:{q}",
            "--dump-json",
            "--flat-playlist",
            "--no-warnings",
            "--quiet"
        ]
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=25)
            for line in res.stdout.splitlines():
                if not line.strip():
                    continue
                item = json.loads(line)
                title = item.get("title", "")
                views = int(item.get("view_count") or 0)
                dur = float(item.get("duration") or 48.0)
                if title:
                    collected.append({
                        "query": q,
                        "title": title,
                        "views": views,
                        "duration_sec": dur
                    })
        except Exception as e:
            print(f"  [Trend Scraper Notice] Query '{q}' skipped: {e}")

    collected.sort(key=lambda x: x.get("views", 0), reverse=True)
    return collected[:15]


# ==============================================================================
# LOOP 1: MULTI-MILLION VIRAL SCRAPER + SELF-EXPANDING PARAMETER DISCOVERY
# ==============================================================================
def run_external_viral_forensics_training(dna: Dict[str, Any]) -> Dict[str, Any]:
    queries = dna.get("topic_engine", {}).get("niche_queries", DEFAULT_TREND_DNA["topic_engine"]["niche_queries"])
    print("\n======================================================================")
    print("LOOP 1: SCRAPING MULTI-MILLION VIRAL SHORTS & DISCOVERING NEW PARAMETERS")
    print("======================================================================")
    samples = _scrape_viral_shorts_metadata(queries, per_query=4)
    top_views = samples[0]["views"] if samples else 0
    print(f"  -> Scraped {len(samples)} top viral Shorts (Highest View Count: {top_views:,} views)")

    existing_params = dna.get("dynamic_discovered_parameters", [])
    existing_ids = [p.get("param_id", "") for p in existing_params]

    sys_prompt = """You are an AI Viral Forensics Scientist studying multi-million-view Indian YouTube Shorts.
Analyze the scraped viral Shorts metadata and current system parameters.
Your task:
1. Identify which collision vector has the strongest viral pull right now.
2. Propose 1 brand-new Devanagari hook skeleton (`<= 17 words`) using `{trigger}` and `{focus}`.
3. DISCOVER 1 TO 2 NEW VIRAL QUALITY PARAMETERS (`newly_discovered_parameters`) not already in `existing_parameter_ids` (for example: 'cognitive_dissonance_contrast', 'personal_wallet_urgency', 'visual_color_polarity_shift', 'curiosity_gap_specificity', 'authority_proof_citation') so our system tracks and optimizes more parameters over time!"""

    user_prompt = json.dumps({
        "scraped_viral_shorts": samples[:12],
        "existing_parameter_ids": existing_ids,
        "required_json_schema": {
            "winning_collision_vector": "authority_panic | hardware_telemetry | hidden_arbitrage | friction_asymmetry",
            "new_hook_template": "Devanagari hook template with {trigger} and {focus} (<=17 words)",
            "extracted_principles": ["3 concise viral insights from these multi-million view videos"],
            "newly_discovered_parameters": [
                {
                    "param_id": "snake_case_parameter_id",
                    "name": "Human-readable parameter name",
                    "rule": "Specific actionable rule for script_agent or video_service to follow",
                    "target_benchmark": "Measurable target benchmark"
                }
            ]
        }
    }, ensure_ascii=False)

    analysis = call_smart_llm_json(sys_prompt, user_prompt, temperature=0.4, cloud_only=True)
    if analysis:
        win_vec = analysis.get("winning_collision_vector", "hardware_telemetry")
        for vec in dna["topic_engine"]["active_collision_vectors"]:
            if vec["id"] == win_vec:
                vec["weight"] = round(min(2.2, float(vec.get("weight", 1.2)) + 0.08), 2)
                print(f"  [Trend Forensics] Boosted winning vector '{win_vec}' -> weight={vec['weight']}x")

        new_hook = str(analysis.get("new_hook_template", "")).strip()
        if "{trigger}" in new_hook and "{focus}" in new_hook and len(new_hook.split()) <= 18:
            hooks = dna["script_engine"]["hook_templates"]
            if not any(h.get("template") == new_hook for h in hooks):
                hooks.append({
                    "id": f"learned_hook_{len(hooks) + 1}",
                    "template": new_hook,
                    "weight": 1.35
                })
                dna["script_engine"]["hook_templates"] = hooks[-8:]
                print(f"  [Trend Forensics] Learned new viral hook template: {new_hook}")

        new_params = analysis.get("newly_discovered_parameters", [])
        if isinstance(new_params, list):
            for np_item in new_params:
                pid = str(np_item.get("param_id", "")).strip()
                if pid and pid not in existing_ids and np_item.get("rule"):
                    np_item["discovered_from"] = f"Viral Forensics ({datetime.now().strftime('%Y-%m-%d')})"
                    existing_params.append(np_item)
                    existing_ids.append(pid)
                    print(f"  [NEW PARAMETER DISCOVERED] '{np_item.get('name')}' -> {np_item.get('rule')}")
            dna["dynamic_discovered_parameters"] = existing_params[-12:]

        principles = analysis.get("extracted_principles", [])
        if isinstance(principles, list) and principles:
            dna["viral_pattern_insights"] = principles[:6]
            for p in principles[:3]:
                print(f"    * Multi-Million Insight: {p}")

    print(f"  [Parameter Evolution] System is now actively enforcing {len(dna['dynamic_discovered_parameters'])} viral parameters.")
    return dna


# ==============================================================================
# LOOP 2: INTERNAL SELF-CRITIQUE & TELEMETRY FEEDBACK LOOP
# ==============================================================================
def sync_internal_self_critique_feedback(dna: Dict[str, Any]) -> Dict[str, Any]:
    print("\n======================================================================")
    print("LOOP 2: SYNCING INTERNAL SELF-CRITIQUE & MULTIMODAL QC TELEMETRY")
    print("======================================================================")
    if not os.path.exists(TELEMETRY_LOG_PATH):
        print("  -> No telemetry log found yet.")
        return dna

    try:
        with open(TELEMETRY_LOG_PATH, "r", encoding="utf-8") as f:
            logs = json.load(f)
    except Exception:
        return dna

    if not logs:
        return dna

    recent = logs[-5:]
    avg_hook_w = sum(r.get("metrics", {}).get("hook_words", 18) for r in recent) / len(recent)
    avg_score = sum(r.get("scores", {}).get("total_viral_readiness_100", 88) for r in recent) / len(recent)

    prof = dna["audio_engine"]["cadence_profiles"]["high_tension_documentary"]
    prof["mid_clause_pause_ms"] = 240
    prof["inter_scene_breath_ms"] = 220

    best_run = max(recent, key=lambda x: x.get("scores", {}).get("total_viral_readiness_100", 0))
    best_vec = best_run.get("collision_vector_id", "")
    if best_vec:
        for vec in dna["topic_engine"]["active_collision_vectors"]:
            if vec["id"] == best_vec:
                vec["weight"] = round(min(2.2, float(vec.get("weight", 1.2)) + 0.05), 2)

    print(
        f"  [Self-Critique Sync] Audited last {len(recent)} runs | "
        f"Avg Readiness: {avg_score:.1f}/100 | Avg Hook: {avg_hook_w:.1f}w | "
        f"Active Discovered Parameters: {len(dna.get('dynamic_discovered_parameters', []))}"
    )
    return dna


def main():
    parser = argparse.ArgumentParser(description="Content Factory V2 — Self-Evolving Trend & Parameter Agent")
    parser.add_argument("--evaluate-video", type=str, default="")
    parser.add_argument("--views", type=int, default=0)
    parser.add_argument("--watch-pct", type=float, default=0.0)
    args = parser.parse_args()

    dna = load_trend_dna()
    dna = run_external_viral_forensics_training(dna)
    dna = sync_internal_self_critique_feedback(dna)
    dna["version"] = f"v2.5-params-{len(dna.get('dynamic_discovered_parameters', []))}-{datetime.now().strftime('%m%d-%H%M')}"
    save_trend_dna(dna)
    print(f"\n[SUCCESS] Saved Self-Evolving Trend DNA ({len(dna.get('dynamic_discovered_parameters', []))} active parameters) -> {TREND_DNA_PATH}\n")


if __name__ == "__main__":
    main()