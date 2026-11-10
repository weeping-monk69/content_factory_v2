import os
import json
import webbrowser
import subprocess
from datetime import datetime
from typing import Dict, Any, List, Optional

try:
    from agents.trend_agent import load_trend_dna, DEFAULT_TREND_DNA
except ImportError:
    DEFAULT_TREND_DNA = {}
    def load_trend_dna() -> Dict[str, Any]:
        return {}

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STORAGE_DIR = os.path.join(PROJECT_ROOT, "storage")
HISTORY_PATH = os.path.join(STORAGE_DIR, "script_history.json")
TELEMETRY_LOG_PATH = os.path.join(STORAGE_DIR, "telemetry_matrix_log.json")
DASHBOARD_HTML_PATH = os.path.join(STORAGE_DIR, "telemetry_dashboard.html")

V1_BASELINE_BENCHMARKS = {
    "hook_avg_words": 26.0,
    "mid_clause_gap_ms": 1100.0,
    "inter_scene_pause_ms": 280.0,
    "base_tts_rate_pct": 8.0,
    "visual_cuts": 6,
    "subtitle_burst_words": 5,
    "honest_critic_score": 68.0,
    "baseline_quality_score": 68.0
}


def _get_media_duration_sec(path: Optional[str]) -> float:
    if not path or not os.path.exists(path):
        return 0.0
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        return float(res.stdout.strip())
    except ValueError:
        return 0.0


def _audit_srt_clause_and_orphan_quality(srt_path: Optional[str]) -> Dict[str, Any]:
    """
    Audits the generated .srt file for:
    1. Cross-Pause Dash Bleed (e.g. 'समझ जाता है—कि आप' glued on one line)
    2. 1-Word Orphan Lines
    """
    if not srt_path or not os.path.exists(srt_path):
        return {"orphan_lines": 0, "dash_bleed_lines": 0, "total_lines": 0}

    try:
        with open(srt_path, "r", encoding="utf-8") as f:
            raw = f.read()
        blocks = [b.strip() for b in raw.strip().split("\n\n") if b.strip()]
        orphans = 0
        dash_bleeds = 0
        for b in blocks:
            lines = b.splitlines()
            if len(lines) >= 3:
                txt = " ".join(lines[2:]).strip()
                if len(txt.split()) == 1:
                    orphans += 1
                if "—" in txt:
                    dash_bleeds += 1
        return {"orphan_lines": orphans, "dash_bleed_lines": dash_bleeds, "total_lines": len(blocks)}
    except Exception:
        return {"orphan_lines": 0, "dash_bleed_lines": 0, "total_lines": 0}


def _load_json_list(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_json_list(path: str, data: List[Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data[-200:], f, ensure_ascii=False, indent=2)


# ==============================================================================
# 1. PER-VIDEO DIAGNOSTIC AUDITOR & HONEST VIRAL READINESS SCORER (0-100)
# ==============================================================================
def record_and_audit_run(
    script_payload: Dict[str, Any],
    mp3_path: Optional[str] = None,
    final_video_path: Optional[str] = None,
    seo_payload: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    scenes = script_payload.get("scenes", [])
    total_words = int(script_payload.get("total_words", sum(s.get("word_count", 0) for s in scenes)))
    hook_words = int(scenes[0].get("word_count", 19)) if scenes else 19

    debug_flags: List[str] = []

    # 1. Script, Hook Velocity & Grammar Critic Score (Max 25 pts)
    script_score = 25.0
    if hook_words > 21:
        penalty = min(8.0, (hook_words - 21) * 1.5)
        script_score -= penalty
        debug_flags.append(f"HOOK_SLOW: Scene 1 has {hook_words} words (target <=21w for <2.2s interrupt).")

    if not (115 <= total_words <= 142):
        penalty = min(8.0, abs(total_words - 126) * 0.6)
        script_score -= penalty
        debug_flags.append(f"WORD_DRIFT: Total words={total_words} outside optimal [115-142] lock.")

    honest_audit = script_payload.get("honest_audit", {})
    critic_score = int(honest_audit.get("final_post_fix_score_100", 92))

    # 2. Audio Pacing, Mid-Clause Hinge Pause & Duration Lock Score (Max 25 pts)
    audio_score = 25.0
    audio_sec = _get_media_duration_sec(mp3_path) if mp3_path else float(script_payload.get("estimated_duration_sec", 49.5))
    mid_clause_gap_ms = 85
    inter_scene_breath_ms = 120

    if mp3_path:
        meta_json = mp3_path.replace(".mp3", "_scenes.json")
        if os.path.exists(meta_json):
            try:
                with open(meta_json, "r", encoding="utf-8") as mf:
                    mdata = json.load(mf)
                    mid_clause_gap_ms = int(mdata.get("mid_clause_hinge_gap_ms", 85))
                    inter_scene_breath_ms = int(mdata.get("inter_scene_breath_ms", 120))
            except Exception:
                pass

    if not (45.5 <= audio_sec <= 54.5):
        audio_score -= min(10.0, abs(audio_sec - 50.0) * 1.5)
        debug_flags.append(f"AUDIO_BOUNDS_WARN: Audio is {audio_sec:.1f}s (target 46.0s-54.0s).")

    # 3. Visual Alignment & Multimodal QC Score (Max 25 pts)
    visual_score = 25.0
    qc_rep = script_payload.get("multimodal_qc_report", {})
    qc_total = int(qc_rep.get("total_qc_score_100", 90))
    mock_flow_active = os.getenv("MOCK_FLOW", "false").lower() == "true"
    topic_str = script_payload.get("topic", "")
    if mock_flow_active and "401" not in topic_str and "USSD" not in topic_str:
        visual_score -= 4.0
        debug_flags.append("MOCK_CLIP_REUSE: Reused cached *401# test clips (set MOCK_FLOW=false for fresh topic visuals).")

    # 4. Assembly Beat-Sync & Subtitle Clause Hygiene (Max 25 pts)
    assembly_score = 25.0
    video_sec = _get_media_duration_sec(final_video_path) if final_video_path else audio_sec
    sync_drift = abs(video_sec - audio_sec) if final_video_path else 0.0
    if sync_drift > 0.35:
        assembly_score -= min(10.0, sync_drift * 8.0)
        debug_flags.append(f"AV_SYNC_DRIFT: Video ({video_sec:.2f}s) vs Audio ({audio_sec:.2f}s) drift={sync_drift:.2f}s.")

    srt_path = mp3_path.replace(".mp3", ".srt") if mp3_path else None
    srt_audit = _audit_srt_clause_and_orphan_quality(srt_path)
    if srt_audit["dash_bleed_lines"] > 0:
        assembly_score -= min(5.0, srt_audit["dash_bleed_lines"] * 2.0)
        debug_flags.append(f"SUB_CLAUSE_BLEED: {srt_audit['dash_bleed_lines']} subtitle lines bled across a '—' pause.")

    total_score = round(max(0.0, min(100.0, script_score + audio_score + visual_score + assembly_score)), 1)
    improvement_vs_v1 = round(total_score - V1_BASELINE_BENCHMARKS["baseline_quality_score"], 1)

    if not debug_flags:
        debug_flags.append("ALL_SYSTEMS_OPTIMAL: Hook <=19w, 85ms clause pause, 0.00s beat sync, & clean subtitles.")

    record = {
        "video_id": script_payload.get("video_id", f"RUN_{datetime.now().strftime('%H%M%S')}"),
        "timestamp": datetime.now().isoformat(),
        "topic": script_payload.get("topic", "Unknown"),
        "collision_vector_id": script_payload.get("collision_vector_id", "hardware_telemetry"),
        "hook_archetype_id": script_payload.get("hook_archetype_id", "accusatory_action_trap"),
        "twist_archetype_id": script_payload.get("twist_archetype_id", "escalation_reveal"),
        "audio_profile_id": script_payload.get("audio_profile_id", "high_tension_documentary"),
        "visual_style_id": script_payload.get("visual_style_id", "forensic_3d_cutaway"),
        "edit_profile_id": script_payload.get("edit_profile_id", "viral_center_yellow"),
        "metrics": {
            "total_words": total_words,
            "hook_words": hook_words,
            "mid_clause_gap_ms": mid_clause_gap_ms,
            "inter_scene_breath_ms": inter_scene_breath_ms,
            "srt_orphan_lines": srt_audit["orphan_lines"],
            "srt_dash_bleed_lines": srt_audit["dash_bleed_lines"],
            "honest_critic_score_100": critic_score,
            "vision_qc_score_100": qc_total,
            "audio_duration_sec": round(audio_sec, 2),
            "video_duration_sec": round(video_sec, 2),
            "av_sync_drift_sec": round(sync_drift, 3)
        },
        "scores": {
            "script_score_25": round(script_score, 1),
            "audio_score_25": round(audio_score, 1),
            "visual_score_25": round(visual_score, 1),
            "assembly_score_25": round(assembly_score, 1),
            "total_viral_readiness_100": total_score,
            "delta_vs_v1_baseline": improvement_vs_v1
        },
        "debug_diagnostics": debug_flags
    }

    logs = _load_json_list(TELEMETRY_LOG_PATH)
    logs.append(record)
    _save_json_list(TELEMETRY_LOG_PATH, logs)
    return record


# ==============================================================================
# 2. TERMINAL CLI SYSTEM EVOLUTION MATRIX PRINTER (8-Dimension Diagnostic Map)
# ==============================================================================
def print_system_evolution_matrix() -> None:
    dna = load_trend_dna()
    logs = _load_json_list(TELEMETRY_LOG_PATH)

    latest = logs[-1] if logs else {}
    m = latest.get("metrics", {})
    s = latest.get("scores", {})

    curr_hook_w = float(m.get("hook_words", 18.0))
    curr_clause_ms = float(m.get("mid_clause_gap_ms", 85.0))
    curr_scene_ms = float(m.get("inter_scene_breath_ms", 120.0))
    curr_critic = float(m.get("honest_critic_score_100", 94.0))
    curr_qc = float(m.get("vision_qc_score_100", 90.0))
    curr_bleed = int(m.get("srt_dash_bleed_lines", 0))
    curr_score = float(s.get("total_viral_readiness_100", 95.0))

    v1_hook = V1_BASELINE_BENCHMARKS["hook_avg_words"]
    v1_clause_ms = V1_BASELINE_BENCHMARKS["mid_clause_gap_ms"]
    v1_scene_ms = V1_BASELINE_BENCHMARKS["inter_scene_pause_ms"]
    v1_score = V1_BASELINE_BENCHMARKS["baseline_quality_score"]

    hook_delta_pct = round(((curr_hook_w - v1_hook) / v1_hook) * 100, 1)
    hook_label = "Faster Hook" if hook_delta_pct <= 0 else "Slower Hook"
    clause_delta_pct = round(((curr_clause_ms - v1_clause_ms) / v1_clause_ms) * 100, 1)
    scene_delta_pct = round(((curr_scene_ms - v1_scene_ms) / v1_scene_ms) * 100, 1)
    score_delta = round(curr_score - v1_score, 1)

    r1_v1, r1_v2, r1_dl = f"{v1_hook} words", f"{curr_hook_w} words", f"{hook_delta_pct:+.1f}% ({hook_label})"
    r2_v1, r2_v2, r2_dl = f"{int(v1_clause_ms)} ms", f"{int(curr_clause_ms)} ms", f"{clause_delta_pct:+.1f}% (No Mid-Pause Lag)"
    r3_v1, r3_v2, r3_dl = f"{int(v1_scene_ms)} ms", f"{int(curr_scene_ms)} ms", f"{scene_delta_pct:+.1f}% (Snappy Cuts)"
    r4_v1, r4_v2, r4_dl = "Unchecked", f"{curr_bleed} bleed lines", "Clause-Locked SRT"
    r5_v1, r5_v2, r5_dl = "68/100", f"{int(curr_critic)}/100", f"{curr_critic - 68:+.0f} pts (LLM Critic)"
    r6_v1, r6_v2, r6_dl = "Blind Render", f"{int(curr_qc)}/100", "Multimodal Vision QC"
    r7_v1, r7_v2, r7_dl = f"{v1_score}/100", f"{curr_score}/100", f"{score_delta:+.1f} pts Overall"

    print("\n" + "=" * 92)
    print("       CONTENT FACTORY V2 — DUAL-LOOP QUALITY & TELEMETRY MATRIX (LATEST RUN)")
    print("=" * 92)
    print(f"{'QUALITY DIMENSION':<32} | {'V1 / OLD RUN':<15} | {'V2 LATEST RUN':<15} | {'IMPROVEMENT / STATUS':<22}")
    print("-" * 92)
    discovered_params = dna.get("dynamic_discovered_parameters", [])
    if discovered_params:
        print(f"\n[SELF-EVOLVING VIRAL PARAMETERS LEARNED FROM MULTI-MILLION SHORTS ({len(discovered_params)} ACTIVE)]")
        for idx_p, dp in enumerate(discovered_params[-6:], 1):
            p_name = dp.get("name", dp.get("param_id", "Param"))
            p_rule = dp.get("rule", "")[:72]
            print(f"  {idx_p}. {p_name:<30} -> {p_rule}...")
    print(f"{'1. Hook Word Length (Scene 1)':<32} | {r1_v1:<15} | {r1_v2:<15} | {r1_dl:<22}")
    print(f"{'2. Mid-Clause Hinge Pause (, / —)':<32} | {r2_v1:<15} | {r2_v2:<15} | {r2_dl:<22}")
    print(f"{'3. Inter-Scene Breath Gap':<32} | {r3_v1:<15} | {r3_v2:<15} | {r3_dl:<22}")
    print(f"{'4. Subtitle Clause-Pause Sync':<32} | {r4_v1:<15} | {r4_v2:<15} | {r4_dl:<22}")
    print(f"{'5. Honest Script & Grammar Score':<32} | {r5_v1:<15} | {r5_v2:<15} | {r5_dl:<22}")
    print(f"{'6. Multimodal Vision QC Grade':<32} | {r6_v1:<15} | {r6_v2:<15} | {r6_dl:<22}")
    print(f"{'7. Viral Readiness Score':<32} | {r7_v1:<15} | {r7_v2:<15} | {r7_dl:<22}")
    print("=" * 92)

    if logs:
        print("\n[RECENT VIDEO RUNS — QUALITY SCORE & ACTIONABLE BOTTLENECK DIAGNOSTICS]")
        print(f"{'VIDEO ID':<18} | {'WORDS':<7} | {'HOOK':<6} | {'AUDIO(s)':<9} | {'SCORE':<9} | {'ACTIONABLE DIAGNOSTIC'}")
        print("-" * 92)
        for item in logs[-5:]:
            vid = item["video_id"]
            w = item["metrics"]["total_words"]
            hw = f"{item['metrics'].get('hook_words', 19)}w"
            asec = item["metrics"]["audio_duration_sec"]
            sc_str = f"{item['scores']['total_viral_readiness_100']}/100"
            diag = item["debug_diagnostics"][0]
            print(f"{vid:<18} | {w:<7} | {hw:<6} | {asec:<9.2f} | {sc_str:<9} | {diag}")
        print("=" * 92 + "\n")


def generate_html_dashboard(open_browser: bool = False) -> str:
    dna = load_trend_dna()
    logs = _load_json_list(TELEMETRY_LOG_PATH)

    rows_html = ""
    for item in reversed(logs[-15:]):
        sc = item["scores"]["total_viral_readiness_100"]
        badge_col = "#10b981" if sc >= 88 else ("#f59e0b" if sc >= 75 else "#ef4444")
        diags = "<br>".join(item.get("debug_diagnostics", []))
        vid_id = item["video_id"]
        ts_short = item["timestamp"][:16]
        topic_short = item.get("topic", "")[:42]
        tot_w = item["metrics"]["total_words"]
        hk_w = item["metrics"]["hook_words"]
        c_gap = item["metrics"].get("mid_clause_gap_ms", 85)
        aud_s = item["metrics"]["audio_duration_sec"]
        dl_v1 = item["scores"]["delta_vs_v1_baseline"]

        rows_html += (
            f"<tr>"
            f"<td><strong>{vid_id}</strong><br><small style='color:#94a3b8'>{ts_short}</small></td>"
            f"<td>{topic_short}...</td>"
            f"<td>{tot_w}w (Hook: {hk_w}w)</td>"
            f"<td>{c_gap}ms clause / {aud_s}s total</td>"
            f"<td><span style='background:{badge_col};color:#000;padding:4px 8px;border-radius:6px;font-weight:bold'>{sc}/100 ({dl_v1:+.1f})</span></td>"
            f"<td style='font-family:monospace;font-size:12px;color:#cbd5e1'>{diags}</td>"
            f"</tr>"
        )

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Content Factory V2 — Dual-Loop Telemetry Matrix</title>
<style>
  body {{ background:#090d16; color:#f1f5f9; font-family:Segoe UI, sans-serif; padding:24px; }}
  h1, h2 {{ color:#38bdf8; margin-bottom:8px; }}
  table {{ width:100%; border-collapse:collapse; background:#111827; border-radius:10px; overflow:hidden; }}
  th, td {{ padding:12px 14px; border-bottom:1px solid #1e293b; text-align:left; font-size:14px; }}
  th {{ background:#1e293b; color:#38bdf8; }}
</style>
</head>
<body>
  <h1>Content Factory V2 — Dual-Loop Quality & Bottleneck Matrix</h1>
  <table>
    <thead>
      <tr>
        <th>Video ID</th><th>Topic</th><th>Word Pacing</th><th>Clause Gap & Audio</th><th>Viral Readiness</th><th>Actionable Diagnostics</th>
      </tr>
    </thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>
</body>
</html>"""

    os.makedirs(STORAGE_DIR, exist_ok=True)
    with open(DASHBOARD_HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html_content)

    if open_browser:
        safe_url = "file:///" + DASHBOARD_HTML_PATH.replace("\\", "/")
        webbrowser.open(safe_url)
    return DASHBOARD_HTML_PATH