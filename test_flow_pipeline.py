import os
from agents.script_agent import generate_viral_script
from services.audio_service import generate_voiceover
from services.video_service import generate_video_with_flow

def run_single_scene_smoke_test():
    print("==================================================")
    print("STEP 1: Generating Script & Forensic Visual Prompt")
    print("==================================================")
    script_data = generate_viral_script()
    scene_1 = script_data["scenes"][0]
    
    print(f"\nTopic       : {script_data['topic']}")
    print(f"Scene 1 Text: {scene_1['narration_hinglish']}")
    print(f"Visual Cue  : {scene_1['visual_prompt']}\n")

    print("==================================================")
    print("STEP 2: Synthesizing Audio & Aligned Subtitles")
    print("==================================================")
    audio_prefix = "storage/audio/smoke_test_scene_1"
    audio_path, srt_path = generate_voiceover(
        scene_1["narration_hinglish"],
        audio_prefix,
        channel="domestic"
    )
    print(f"Audio ready: {audio_path}")
    print(f"SRT ready  : {srt_path}\n")

    print("==================================================")
    print("STEP 3: Submitting Visual Prompt to Google Flow")
    print("==================================================")
    output_video_path = "storage/videos/smoke_test_scene_1.mp4"
    os.makedirs(os.path.dirname(output_video_path), exist_ok=True)
    
    video_path = generate_video_with_flow(
        prompt=scene_1["visual_prompt"],
        output_path=output_video_path
    )
    
    print(f"\n[DONE] Scene 1 video generated successfully: {video_path}")

if __name__ == "__main__":
    run_single_scene_smoke_test()