import os
import json
from services.audio_service import generate_voiceover

# Read the latest generated script directly from storage
history_file = "storage/script_history.json"
if os.path.exists(history_file):
    with open(history_file, "r", encoding="utf-8") as f:
        history = json.load(f)
    latest_script = history[-1]
    
    print(f"Loaded: {latest_script['topic']}")
    print(f"Hook  : {latest_script.get('hook_banner_domestic') or latest_script.get('hook_banner')}\n")
    
    beats = [s.get("narration_hinglish") or s.get("narration_english") for s in latest_script["scenes"]]
    full_text = " ... ".join([b for b in beats if b])
else:
    full_text = "जिस सेकंड आपने वो लिंक खोला, आपका बैंक अकाउंट आधा खाली हो चुका था। लेकिन असली खेल इसके बाद शुरू होता है।"

print("--- NARRATION TEXT ---")
print(full_text)
print("----------------------\n")

out_prefix = "storage/audio/latest_script_audio"
audio_file, srt_file = generate_voiceover(full_text, out_prefix, channel="domestic")

print(f"\nSuccess! Audio file: {os.path.abspath(audio_file)}")
print(f"Subtitle file: {os.path.abspath(srt_file)}")

# Play audio in default Windows player
os.system(f'start "" "{os.path.abspath(audio_file)}"')