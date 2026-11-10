import os
import sys

# 1. Pipeline Imports
from agents.script_agent import generate_viral_script
from services.audio_service import generate_voiceover
from services.video_service import generate_all_scenes_in_one_prompt
from services.assembly_service import tailor_clips_and_assemble_viral_reel
from services.qc_agent import audit_and_auto_patch_rendered_reel
from services.telemetry_service import (
    record_and_audit_run,
    print_system_evolution_matrix,
    generate_html_dashboard
)

try:
    from agents.seo_agent import generate_and_critique_seo_metadata
except ImportError:
    generate_and_critique_seo_metadata = None

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
STORAGE_DIR = os.path.join(PROJECT_ROOT, "storage")
AUDIO_DIR = os.path.join(STORAGE_DIR, "audio")
VIDEOS_DIR = os.path.join(STORAGE_DIR, "videos")

os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(VIDEOS_DIR, exist_ok=True)

QC_PASS_THRESHOLD = int(os.getenv("QC_PASS_THRESHOLD", "88"))


def _render_audio_video_pass(script_data: dict, pass_label: str = "PASS_1"):
    """Executes Audio Synthesis + Video Prompt Critic + Beat-Locked FFmpeg Assembly."""
    video_id = script_data.get("video_id", "EXP_DEMO_001")
    num_scenes = len(script_data.get("scenes", []))

    print(f"\n=======================================================")
    print(f"STAGE 2 [{pass_label}]: SYNTHESIZING {num_scenes}-SCENE AUDIO & SFX")
    print(f"=======================================================")
    audio_base = os.path.join(AUDIO_DIR, f"{video_id}_narration")
    mp3_file, srt_file = generate_voiceover(
        text=script_data["scenes"][0]["narration_hinglish"],
        output_base_path=audio_base,
        scenes=script_data["scenes"]
    )

    print(f"\n=======================================================")
    print(f"STAGE 3 [{pass_label}]: PRODUCING CLIPS VIA VIDEO SELF-CRITIC")
    print(f"=======================================================")
    clips = generate_all_scenes_in_one_prompt(script_data["scenes"])

    print(f"\n=======================================================")
    print(f"STAGE 4A [{pass_label}]: BEAT-LOCKED {num_scenes}-SCENE ASSEMBLY")
    print(f"=======================================================")
    final_video = os.path.join(VIDEOS_DIR, f"{video_id}_reel.mp4")
    assembled_path = tailor_clips_and_assemble_viral_reel(
        clip_paths=clips,
        audio_path=mp3_file,
        srt_path=srt_file,
        output_path=final_video,
        num_visual_cuts=num_scenes
    )
    return mp3_file, srt_file, assembled_path


def main():
    print("\n=======================================================")
    print("STAGE 1: GENERATING SCRIPT VIA TREND DNA & HONEST CRITIC")
    print("=======================================================")
    script_data = generate_viral_script()

    seo_payload = None
    if generate_and_critique_seo_metadata:
        seo_payload = generate_and_critique_seo_metadata(script_data)
        print(f"\n[SEO Title] {seo_payload.get('title')}")

    # Initial Render Pass
    mp3_file, srt_file, assembled_path = _render_audio_video_pass(script_data, pass_label="INITIAL_RENDER")

    print("\n=======================================================")
    print("STAGE 4B: MULTIMODAL VISION QC AUDIT OF FINAL REEL")
    print("=======================================================")
    qc_report = audit_and_auto_patch_rendered_reel(
        video_path=assembled_path,
        script_data=script_data,
        audio_path=mp3_file,
        pass_threshold=QC_PASS_THRESHOLD
    )

    # STAGE 5: RECURSIVE AUTO-FIX (If QC score < 88, patch scenes & re-render automatically)
    if qc_report.get("needs_rerender"):
        print("\n=======================================================")
        print(f"STAGE 5: RECURSIVE AUTO-FIX TRIGGERED (Score {qc_report['total_qc_score_100']} < {QC_PASS_THRESHOLD})")
        print(f"Patching Failed Scenes {qc_report.get('failed_scene_numbers')} and Re-Rendering...")
        print("=======================================================")
        script_data["scenes"] = qc_report["patched_scenes"]
        script_data["total_words"] = sum(s["word_count"] for s in script_data["scenes"])
        mp3_file, srt_file, assembled_path = _render_audio_video_pass(script_data, pass_label="RECURSIVE_FIX")

        qc_report = audit_and_auto_patch_rendered_reel(
            video_path=assembled_path,
            script_data=script_data,
            audio_path=mp3_file,
            pass_threshold=QC_PASS_THRESHOLD
        )

    print("\n=======================================================")
    print("STAGE 6: UPDATING TELEMETRY & SYSTEM EVOLUTION MATRIX")
    print("=======================================================")
    script_data["multimodal_qc_report"] = qc_report
    audit_record = record_and_audit_run(
        script_payload=script_data,
        mp3_path=mp3_file,
        final_video_path=assembled_path,
        seo_payload=seo_payload
    )

    print_system_evolution_matrix()
    generate_html_dashboard(open_browser=False)

    print(f"\n[DONE] Final Viral Reel: {assembled_path}")
    print(f"Multimodal Vision QC Score : {qc_report.get('total_qc_score_100')}/100 [{qc_report.get('verdict')}]")
    print(f"System Telemetry Readiness : {audit_record['scores']['total_viral_readiness_100']}/100")


if __name__ == "__main__":
    main()