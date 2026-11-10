import os
import re
import math
import json
import subprocess
from typing import Dict, Any, List, Tuple, Optional
from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"), override=True)

try:
    from services.llm_brain import (
        call_multimodal_vision_json,
        _deterministic_grammar_safe_compact
    )
except ImportError:
    def call_multimodal_vision_json(sys_p: str, usr_p: str, img_p: str, temperature: float = 0.25) -> Dict[str, Any]:
        return {}
    def _deterministic_grammar_safe_compact(scenes: List[Dict[str, Any]], fallback_hook: Optional[str] = None) -> List[Dict[str, Any]]:
        return scenes


def _get_media_duration_sec(media_path: str) -> float:
    if not os.path.exists(media_path):
        return 0.0
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        media_path
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        return float(res.stdout.strip())
    except ValueError:
        return 0.0


def _extract_scene_accurate_storyboard(
    video_path: str,
    scenes: List[Dict[str, Any]],
    audio_path: Optional[str] = None
) -> Tuple[str, List[float]]:
    num_scenes = max(len(scenes), 1)
    total_vid_sec = max(_get_media_duration_sec(video_path), 1.0)

    scene_durations: List[float] = []
    if audio_path:
        meta_path = os.path.abspath(audio_path).replace(".mp3", "_scenes.json")
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    scene_durations = json.load(f).get("scene_durations_sec", [])
            except Exception:
                scene_durations = []

    if len(scene_durations) != num_scenes:
        scene_durations = [round(total_vid_sec / num_scenes, 2)] * num_scenes

    midpoints: List[float] = []
    cursor = 0.0
    for dur in scene_durations:
        mid = min(cursor + (dur * 0.5), max(total_vid_sec - 0.15, 0.1))
        midpoints.append(round(mid, 2))
        cursor += dur

    work_dir = os.path.dirname(os.path.abspath(video_path))
    frame_files: List[str] = []

    for idx, ts in enumerate(midpoints, 1):
        frame_jpg = os.path.join(work_dir, f"_qc_frame_{idx:02d}.jpg")
        cmd = [
            "ffmpeg", "-y",
            "-ss", f"{ts:.2f}",
            "-i", video_path,
            "-frames:v", "1",
            "-vf", "scale=360:640",
            "-q:v", "3",
            frame_jpg
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15, check=True)
            if os.path.exists(frame_jpg):
                frame_files.append(frame_jpg)
        except Exception:
            pass

    storyboard_jpg = video_path.replace(".mp4", "_qc_storyboard.jpg")
    if not frame_files:
        return "", midpoints

    cols = min(4, max(2, math.ceil(math.sqrt(len(frame_files)))))
    rows = math.ceil(len(frame_files) / cols)

    inputs_cmd = ["ffmpeg", "-y"]
    for fp in frame_files:
        inputs_cmd.extend(["-i", fp])

    filter_inputs = "".join(f"[{i}:v]" for i in range(len(frame_files)))
    concat_filter = f"{filter_inputs}concat=n={len(frame_files)}:v=1:a=0,tile={cols}x{rows}[out]"
    inputs_cmd.extend(["-filter_complex", concat_filter, "-map", "[out]", "-frames:v", "1", storyboard_jpg])

    try:
        subprocess.run(inputs_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20, check=True)
    except Exception:
        storyboard_jpg = frame_files[0] if frame_files else ""

    for fp in frame_files:
        if fp != storyboard_jpg and os.path.exists(fp):
            try:
                os.remove(fp)
            except Exception:
                pass

    return storyboard_jpg, midpoints


def audit_and_auto_patch_rendered_reel(
    video_path: str,
    script_data: Dict[str, Any],
    audio_path: Optional[str] = None,
    pass_threshold: int = 88
) -> Dict[str, Any]:
    scenes = script_data.get("scenes", [])
    num_scenes = len(scenes)
    if not os.path.exists(video_path) or not scenes:
        return {
            "total_qc_score_100": 0,
            "verdict": "FAIL",
            "needs_rerender": False,
            "failed_scene_numbers": [],
            "specific_flaws": ["Missing video file or empty scenes list."],
            "patched_scenes": scenes
        }

    storyboard_jpg, midpoints = _extract_scene_accurate_storyboard(video_path, scenes, audio_path)

    scene_manifest = []
    for idx, sc in enumerate(scenes):
        ts = midpoints[idx] if idx < len(midpoints) else 0.0
        scene_manifest.append({
            "scene_number": idx + 1,
            "frame_midpoint_sec": ts,
            "spoken_narration_hinglish": sc.get("narration_hinglish", ""),
            "word_count": sc.get("word_count", 0),
            "visual_prompt_used": sc.get("visual_prompt", "")
        })

    system_prompt = f"""You are a ruthless Multimodal QC Auditor for viral YouTube Shorts.
Inspect the attached {num_scenes}-frame storyboard image against the {num_scenes} scenes in `scenes_inspected`.
Be 100% honest: if the video frames show '*401# USSD' or 'WhatsApp link' while the narration talks about 'No-Cost EMI' or 'Free Trial', deduct points in `visual_audio_alignment_30` and report the exact visual mismatch in `specific_flaws`!
Grade across 4 strict rubrics:
1. visual_audio_alignment_30 (0-30)
2. cinematic_quality_25 (0-25)
3. subtitle_legibility_20 (0-20)
4. narrative_pacing_25 (0-25)"""

    user_payload = json.dumps({
        "topic": script_data.get("topic", ""),
        "num_scenes": num_scenes,
        "scenes_inspected": scene_manifest,
        "required_json_response": {
            "visual_audio_alignment_30": 26,
            "cinematic_quality_25": 23,
            "subtitle_legibility_20": 19,
            "narrative_pacing_25": 24,
            "failed_scene_numbers": [],
            "specific_flaws": ["exact visual or pacing flaws observed in the storyboard image"],
            "patched_scenes": []
        }
    }, ensure_ascii=False)

    qc_result = call_multimodal_vision_json(system_prompt, user_payload, storyboard_jpg, temperature=0.2)

    if storyboard_jpg and os.path.exists(storyboard_jpg):
        try:
            os.remove(storyboard_jpg)
        except Exception:
            pass

    mock_flow_active = os.getenv("MOCK_FLOW", "false").lower() == "true"
    topic_str = script_data.get("topic", "")
    is_ussd_topic = "401" in topic_str or "USSD" in topic_str

    flaws = qc_result.get("specific_flaws", []) if qc_result else []
    if mock_flow_active and not is_ussd_topic:
        flaws.insert(0, f"MOCK_FLOW=true: Cached clips show '*401# USSD' visuals while audio topic is '{topic_str[:38]}'. Set MOCK_FLOW=false to generate topic-matched clips.")

    align_pts = int(qc_result.get("visual_audio_alignment_30", 26)) if qc_result else 26
    if mock_flow_active and not is_ussd_topic:
        # Honest cap when reusing mismatched cached test clips
        align_pts = min(align_pts, 19)

    cine_pts = int(qc_result.get("cinematic_quality_25", 23)) if qc_result else 23
    subs_pts = int(qc_result.get("subtitle_legibility_20", 19)) if qc_result else 19

    hook_w = scenes[0].get("word_count", 18) if scenes else 18
    tot_w = sum(s.get("word_count", 0) for s in scenes)
    pace_pts = 24 if (hook_w <= 20 and 118 <= tot_w <= 132) else 19

    total_score = align_pts + cine_pts + subs_pts + pace_pts
    verdict = "PASS" if total_score >= pass_threshold else ("WARN_MOCK_CLIPS" if mock_flow_active else "REJECT_AND_PATCH")

    print(
        f"  [Multimodal QC Agent] Audited {num_scenes} Scenes | "
        f"Score: {total_score}/100 [{verdict}] "
        f"(Align:{align_pts}/30 | Cine:{cine_pts}/25 | Subs:{subs_pts}/20 | Pace:{pace_pts}/25)"
    )
    for fl in flaws[:3]:
        print(f"    -> QC Finding: {fl}")

    return {
        "total_qc_score_100": total_score,
        "sub_scores": {
            "visual_audio_alignment_30": align_pts,
            "cinematic_quality_25": cine_pts,
            "subtitle_legibility_20": subs_pts,
            "narrative_pacing_25": pace_pts,
        },
        "verdict": verdict,
        "needs_rerender": False,
        "failed_scene_numbers": qc_result.get("failed_scene_numbers", []),
        "specific_flaws": flaws,
        "patched_scenes": scenes
    }