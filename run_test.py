import os
from agents.script_agent import generate_viral_script
from services.audio_service import generate_voiceover

print("Generating new forensic script blueprint...")
script_data = generate_viral_script()

# Collect all 8 Hinglish narration beats
narration_beats = [scene["narration_hinglish"] for scene in script_data["scenes"]]
full_text = " , ".join(narration_beats)

print("\n--- NEW HINGLISH NARRATION ---")
print(full_text)
print("------------------------------\n")

# Synthesize audio and aligned .srt subtitles
audio_path, srt_path = generate_voiceover(full_text, "storage/audio/latest_script_audio", channel="domestic")

print(f"\nSuccess!")
print(f"Audio file: {os.path.abspath(audio_path)}")
print(f"Subtitle file: {os.path.abspath(srt_path)}")

# Open the audio in Windows media player
os.system(f'start "" "{os.path.abspath(audio_path)}"')