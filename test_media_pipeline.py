import os
from services.audio_service import generate_voiceover
from services.video_service import generate_video_with_flow
from services.editor_service import assemble_short

def test_full_pipeline():
    prompt = "Cinematic 35mm lens, close-up of a craftsman in a leather apron slowly pouring coffee beans into a vintage brass grinder, dramatic side lighting, warm atmospheric dust particles."
    script = "Most people think motivation is a feeling. Neurochemically, it is dopamine anticipating reward. Fix the stimulus, and focus follows automatically."
    
    raw_video = "storage/raw_video/test_clip.mp4"
    audio_file, srt_file = generate_voiceover(script, output_prefix="storage/audio/test_speech")
    
    print("\n[Step 1/3] Generated audio and subtitle files.")
    
    print("\n[Step 2/3] Generating raw video via AI Pro Playwright...")
    generate_video_with_flow(prompt, raw_video)
    
    print("\n[Step 3/3] Assembling vertical short (9:16 crop, ducking, subtitles)...")
    final_output = "storage/final_output/test_short_complete.mp4"
    assemble_short(raw_video, audio_file, srt_file, final_output)
    
    assert os.path.exists(final_output), "Error: Final video output was not created."
    print(f"\nMEDIA PIPELINE VERIFIED! Watch your rendered Short at:\n{final_output}")

if __name__ == "__main__":
    test_full_pipeline()