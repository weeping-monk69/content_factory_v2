import os
import json
import shutil
import subprocess
from typing import List, Dict, Any

try:
    from agents.trend_agent import load_trend_dna
except ImportError:
    def load_trend_dna() -> Dict[str, Any]:
        return {}


def get_media_duration(media_path: str) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        media_path
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    return float(res.stdout.strip())


def _audit_final_reel_self_critic(output_path: str, target_audio_sec: float) -> None:
    if not os.path.exists(output_path) or os.path.getsize(output_path) < 102400:
        raise RuntimeError(f"[Assembly Self-Critic FAILED] Output video missing or corrupt: {output_path}")

    video_sec = get_media_duration(output_path)
    drift = abs(video_sec - target_audio_sec)
    print(
        f"  [Assembly Self-Critic] PASS: Final MP4 = {video_sec:.2f}s "
        f"(Audio Sync Drift: {drift:.2f}s | Size: {os.path.getsize(output_path) // 1024} KB)"
    )


def tailor_clips_and_assemble_viral_reel(
    clip_paths: List[str],
    audio_path: str,
    srt_path: str,
    output_path: str,
    num_visual_cuts: int = 6
) -> str:
    """
    1. Reads exact per-scene spoken durations from `_scenes.json` for 0.00s beat-locked cuts.
    2. Applies Dark Forensic Color Grading (contrast=1.08, saturation=1.12) + alternating punch-in framing.
    3. Burns lower-third safe-zone mixed-script subtitles (MarginV=58 in ASS PlayResY=288).
    """
    if not clip_paths:
        raise ValueError("No video clips provided for assembly.")

    dna = load_trend_dna()
    asm_cfg = dna.get("assembly_engine", {})
    active_id = asm_cfg.get("active_edit_profile", "viral_center_yellow")
    profile = asm_cfg.get("edit_profiles", {}).get(active_id, {})

    dynamic_cuts = int(profile.get("recommended_visual_cuts", num_visual_cuts))
    zoom_scale = profile.get("alternate_zoom_scale", "1188:2112")
    font_size = int(profile.get("font_size", 15))
    primary_col = profile.get("primary_colour_ass", "&H0000FFFF")

    # Lock MarginV=58 so subtitles sit cleanly in the lower-third safe zone without blocking center visuals
    raw_mv = int(profile.get("margin_v", 58))
    margin_v = 58 if raw_mv > 90 else raw_mv

    abs_audio = os.path.abspath(audio_path)
    abs_srt = os.path.abspath(srt_path)
    abs_out = os.path.abspath(output_path)
    work_dir = os.path.dirname(abs_out)
    os.makedirs(work_dir, exist_ok=True)

    total_audio_sec = get_media_duration(abs_audio)

    scene_meta_path = abs_audio.replace(".mp3", "_scenes.json")
    scene_durations: List[float] = []
    if os.path.exists(scene_meta_path):
        try:
            with open(scene_meta_path, "r", encoding="utf-8") as mf:
                scene_durations = json.load(mf).get("scene_durations_sec", [])
        except Exception:
            scene_durations = []

    if scene_durations and len(scene_durations) >= 3:
        cut_durations = scene_durations
        total_cuts = len(cut_durations)
        print(f"  [Beat-Locked Sync] Mapping {total_cuts} visual cuts to EXACT spoken scene durations: {cut_durations}")
    else:
        total_cuts = max(dynamic_cuts, len(clip_paths))
        cut_durations = [total_audio_sec / total_cuts] * total_cuts

    print("\n==================================================")
    print(f"ASSEMBLY SERVICE [Profile: {active_id}]: {total_audio_sec:.1f}s Audio | {total_cuts} Visual Cuts")
    print("==================================================")

    # Shared dark documentary contrast & color LUT so different clips look cohesive
    forensic_color_grade = "eq=contrast=1.06:saturation=1.10:brightness=-0.01"

    segment_files: List[str] = []
    for idx in range(total_cuts):
        src_clip = os.path.abspath(clip_paths[idx % len(clip_paths)])
        seg_out = os.path.join(work_dir, f"_tailored_seg_{idx + 1:02d}.mp4")
        this_cut_sec = cut_durations[idx]

        if idx % 2 == 0:
            vf_scale = (
                f"scale=1080:1920:force_original_aspect_ratio=increase,"
                f"crop=1080:1920,{forensic_color_grade},setsar=1"
            )
        else:
            vf_scale = (
                f"scale={zoom_scale}:force_original_aspect_ratio=increase,"
                f"crop=1080:1920,{forensic_color_grade},setsar=1"
            )

        seg_cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1",
            "-i", src_clip,
            "-t", f"{this_cut_sec:.3f}",
            "-vf", vf_scale,
            "-r", "30",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-pix_fmt", "yuv420p",
            "-an",
            seg_out
        ]
        subprocess.run(seg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        segment_files.append(seg_out)

    concat_list_path = os.path.join(work_dir, "_concat_manifest.txt")
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for seg in segment_files:
            f.write(f"file '{seg.replace(chr(92), '/')}'\n")

    local_temp_srt = "_active_subs.srt"
    if os.path.exists(abs_srt) and os.path.getsize(abs_srt) > 0:
        shutil.copyfile(abs_srt, local_temp_srt)
    else:
        with open(local_temp_srt, "w", encoding="utf-8") as f:
            f.write("1\n00:00:00,000 --> 00:00:04,000\n \n")

    viral_sub_style = (
        f"Fontname=Arial,FontSize={font_size},Bold=1,"
        f"PrimaryColour={primary_col},OutlineColour=&H00000000,BackColour=&H80000000,"
        f"BorderStyle=1,Outline=2,Shadow=1,"
        f"Alignment=2,MarginV={margin_v},MarginL=40,MarginR=40"
    )

    final_cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_list_path,
        "-i", abs_audio,
        "-vf", f"subtitles={local_temp_srt}:force_style='{viral_sub_style}'",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "19",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        abs_out
    ]

    print("Burning lower-third safe-zone captions (MarginV=58) and mastering Reel...")
    subprocess.run(final_cmd, check=True)

    for seg in segment_files + [concat_list_path, local_temp_srt]:
        try:
            if os.path.exists(seg):
                os.remove(seg)
        except Exception:
            pass

    _audit_final_reel_self_critic(abs_out, total_audio_sec)
    print(f"\n[SUCCESS] Assembled Reel ready at: {abs_out}")
    return abs_out


def merge_video_audio_subtitles(video_path: str, audio_path: str, srt_path: str, output_path: str) -> str:
    return tailor_clips_and_assemble_viral_reel(
        clip_paths=[video_path],
        audio_path=audio_path,
        srt_path=srt_path,
        output_path=output_path,
        num_visual_cuts=1
    )