import subprocess
import os
import shutil

def assemble_short(raw_video: str, voiceover_audio: str, srt_path: str, output_path: str) -> str:
    """
    Combines raw video, voiceover, and subtitles into a finished 9:16 vertical Short (1080x1920).
    Uses root-level temporary subtitle file to bypass Windows libass path bugs.
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
    abs_raw = os.path.abspath(raw_video)
    abs_audio = os.path.abspath(voiceover_audio)
    abs_output = os.path.abspath(output_path)
    abs_srt = os.path.abspath(srt_path)

    os.makedirs(os.path.dirname(abs_output), exist_ok=True)

    # Subtitle staging
    temp_srt_name = "active_render_subs.srt"
    temp_srt_path = os.path.join(project_root, temp_srt_name)
    shutil.copy2(abs_srt, temp_srt_path)

    # Subtitle styling scaled for 1080x1920 (FontSize=52, MarginV=280)
    sub_style = (
        "FontName=Arial,FontSize=52,Bold=1,"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=4.0,Alignment=2,MarginV=280"
    )
    
    # Crop to 9:16, scale up to crisp 1080x1920, burn subtitles
    filter_complex = (
        f"[0:v]crop=ih*(9/16):ih,scale=1080:1920:flags=lanczos,subtitles={temp_srt_name}:force_style='{sub_style}'[v];"
        f"[0:a]volume=0.20[ambient];"
        f"[ambient][1:a]amix=inputs=2:duration=first[a]"
    )
    
    cmd = [
        "ffmpeg", "-y",
        "-i", abs_raw,
        "-i", abs_audio,
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", "[a]",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        abs_output
    ]
    
    print(f"Running FFmpeg assembly on: {output_path} (1080x1920)...")
    try:
        subprocess.run(cmd, cwd=project_root, check=True)
        print("Assembly complete.")
    finally:
        if os.path.exists(temp_srt_path):
            os.remove(temp_srt_path)
            
    return output_path