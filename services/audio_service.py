import os
import re
import json
import asyncio
import subprocess
from typing import List, Dict, Any, Tuple, Optional
import edge_tts

try:
    from agents.trend_agent import load_trend_dna
except ImportError:
    def load_trend_dna() -> Dict[str, Any]:
        return {}

VOICE_GENDER = os.getenv("VOICE_GENDER", "male").lower().strip()

# ==============================================================================
# CONFIGURABLE NATURAL PAUSE TIMINGS (200ms - 300ms Sweet Spot)
# Adjust MID_CLAUSE_PAUSE_MS anywhere between 200 and 300 (default: 240ms)
# ==============================================================================
MID_CLAUSE_PAUSE_MS = int(os.getenv("MID_CLAUSE_PAUSE_MS", "240"))
INTER_SCENE_BREATH_MS = int(os.getenv("INTER_SCENE_BREATH_MS", "220"))

INDIAN_VOICES = {
    "female": "hi-IN-SwaraNeural",
    "male": "hi-IN-MadhurNeural"
}

SCENE_EMOTION_PROFILES = {
    1: {
        "name": "Hook (Urgent Pattern Interrupt)",
        "setup_pitch": "+2Hz", "setup_rate": "+9%",
        "reveal_pitch": "-1Hz", "reveal_rate": "+7%"
    },
    2: {
        "name": "Mechanism (Investigative Expose)",
        "setup_pitch": "+0Hz", "setup_rate": "+8%",
        "reveal_pitch": "-2Hz", "reveal_rate": "+6%"
    },
    3: {
        "name": "Forensic Proof (Hard-Hitting Data)",
        "setup_pitch": "+1Hz", "setup_rate": "+9%",
        "reveal_pitch": "-1Hz", "reveal_rate": "+6%"
    },
    4: {
        "name": "Escalation Twist (Dark Conspiracy)",
        "setup_pitch": "-1Hz", "setup_rate": "+7%",
        "reveal_pitch": "-3Hz", "reveal_rate": "+5%"
    },
    5: {
        "name": "The Seekh (Commanding Solution)",
        "setup_pitch": "+2Hz", "setup_rate": "+8%",
        "reveal_pitch": "+0Hz", "reveal_rate": "+7%"
    },
    6: {
        "name": "Cliffhanger (Suspense Teaser)",
        "setup_pitch": "-1Hz", "setup_rate": "+7%",
        "reveal_pitch": "+2Hz", "reveal_rate": "+9%"
    },
}

DEVANAGARI_TO_ENGLISH_SUB_MAP = {
    "डार्क पैटर्न": "Dark Pattern",
    "डायनेमिक प्राइसिंग": "Dynamic Pricing",
    "सर्ज प्राइसिंग": "Surge Pricing",
    "टेलीमेट्री": "Telemetry",
    "एल्गोरिदम": "Algorithm",
    "ओटीपी": "OTP",
    "यूपीआई": "UPI",
    "पार्ट टू": "PART 2",
    "पार्ट 2": "PART 2",
    "ईएमआई": "EMI",
    "जीएसटी": "GST",
    "आरबीआई": "RBI",
    "सिबिल": "CIBIL",
    "क्रेडिट कार्ड": "Credit Card",
    "बैकग्राउंड": "Background",
    "सेटिंग्स": "Settings",
    "प्राइवेसी": "Privacy",
    "परमिशन": "Permission",
    "सेंसर": "Sensor",
    "बैटरी": "Battery",
    "क्लिपबोर्ड": "Clipboard",
}


def _get_audio_duration_ms(audio_path: str) -> float:
    if not os.path.exists(audio_path):
        return 0.0
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        return float(res.stdout.strip()) * 1000.0
    except ValueError:
        return 0.0


def _normalize_hinge_punctuation(text: str) -> str:
    out = text.replace("पार्ट 2", "पार्ट टू").replace("PART 2", "पार्ट टू")
    out = re.sub(r"—\s*यह\s+अभी", "? अभी", out)
    out = re.sub(r"\s*—\s*", "— ", out)
    out = re.sub(r"\s+", " ", out).strip()
    return out


def _split_scene_into_setup_and_reveal(text: str) -> List[str]:
    clean = _normalize_hinge_punctuation(text)

    for sep in ["— ", ", ", "? ", "! "]:
        if sep in clean:
            parts = clean.split(sep, 1)
            if sep.strip() in ["?", "!"]:
                p1 = (parts[0].strip() + sep.strip()).strip()
            elif sep.strip() == ",":
                p1 = (parts[0].strip() + ",").strip()
            else:
                p1 = parts[0].strip()
            p2 = parts[1].strip()
            if len(p1.split()) >= 3 and len(p2.split()) >= 3:
                return [p1, p2]

    for conj in [" लेकिन ", " इसलिए ", " ताकि ", " क्योंकि "]:
        if conj in clean:
            idx = clean.find(conj)
            p1 = clean[:idx].strip()
            p2 = clean[idx:].strip()
            if len(p1.split()) >= 4 and len(p2.split()) >= 4:
                return [p1, p2]

    return [clean]


def _trim_sub_clause_ffmpeg(
    raw_clause_mp3: str,
    trimmed_clause_mp3: str,
    is_first_clause: bool,
    has_second_clause: bool,
    clause_pause_ms: int = MID_CLAUSE_PAUSE_MS
) -> None:
    """
    Trims Edge-TTS dead air from each sub-clause and injects the exact
    200-300ms (default 240ms) natural human pause at ',' or '—'.
    """
    pad_sec = f"{clause_pause_ms / 1000.0:.3f}" if (is_first_clause and has_second_clause) else "0.020"
    af_clause = (
        "silenceremove=start_periods=1:start_silence=0.01:start_threshold=-42dB,"
        "areverse,"
        "silenceremove=start_periods=1:start_silence=0.02:start_threshold=-42dB,"
        "areverse,"
        f"apad=pad_dur={pad_sec}"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-i", raw_clause_mp3, "-af", af_clause, "-c:a", "libmp3lame", "-b:a", "192k", trimmed_clause_mp3],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
    )


def _shape_scene_with_cinematic_whoosh_and_breath(
    raw_mp3: str,
    shaped_mp3: str,
    scene_idx: int,
    scene_breath_ms: int = INTER_SCENE_BREATH_MS
) -> None:
    """
    1. Appends a natural inter-scene breath pad (default 220ms).
    2. Mixes a subtle sub-bass impact + filtered pink-noise whoosh at the scene cut.
    """
    clean_voice_tmp = shaped_mp3.replace(".mp3", "_clean_v.mp3")
    sfx_tmp = shaped_mp3.replace(".mp3", "_sfx.mp3")
    breath_sec = f"{scene_breath_ms / 1000.0:.3f}"

    af_voice = (
        "silenceremove=start_periods=1:start_silence=0.01:start_threshold=-45dB,"
        "areverse,"
        "silenceremove=start_periods=1:start_silence=0.02:start_threshold=-45dB,"
        "areverse,"
        f"apad=pad_dur={breath_sec}"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-i", raw_mp3, "-af", af_voice, "-c:a", "libmp3lame", "-b:a", "192k", clean_voice_tmp],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
    )

    if scene_idx == 1:
        sfx_dur = 0.42
        sfx_filter = (
            f"anoisesrc=d={sfx_dur:.2f}:c=pink:r=24000:a=0.14,lowpass=f=220,"
            f"afade=t=in:st=0:d=0.02,afade=t=out:st=0.08:d={sfx_dur-0.08:.2f},volume=0.32[n];"
            f"sine=frequency=52:sample_rate=24000:duration={sfx_dur:.2f},"
            f"afade=t=out:st=0.05:d={sfx_dur-0.05:.2f},volume=0.42[s];"
            "[n][s]amix=inputs=2:normalize=0"
        )
    elif scene_idx == 4:
        sfx_dur = 0.35
        sfx_filter = (
            f"anoisesrc=d={sfx_dur:.2f}:c=pink:r=24000:a=0.11,lowpass=f=250,"
            f"afade=t=in:st=0:d=0.02,afade=t=out:st=0.06:d={sfx_dur-0.06:.2f},volume=0.26[n];"
            f"sine=frequency=60:sample_rate=24000:duration={sfx_dur:.2f},"
            f"afade=t=out:st=0.04:d={sfx_dur-0.04:.2f},volume=0.35[s];"
            "[n][s]amix=inputs=2:normalize=0"
        )
    else:
        sfx_dur = 0.25
        sfx_filter = (
            f"anoisesrc=d={sfx_dur:.2f}:c=pink:r=24000:a=0.07,lowpass=f=280,"
            f"afade=t=in:st=0:d=0.01,afade=t=out:st=0.04:d={sfx_dur-0.04:.2f},volume=0.18[n];"
            f"sine=frequency=68:sample_rate=24000:duration={sfx_dur:.2f},"
            f"afade=t=out:st=0.03:d={sfx_dur-0.03:.2f},volume=0.28[s];"
            "[n][s]amix=inputs=2:normalize=0"
        )

    try:
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", sfx_filter, "-c:a", "libmp3lame", "-b:a", "128k", sfx_tmp],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
        )
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", clean_voice_tmp,
                "-i", sfx_tmp,
                "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[out]",
                "-map", "[out]",
                "-c:a", "libmp3lame", "-b:a", "192k",
                shaped_mp3
            ],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
        )
    except Exception:
        os.replace(clean_voice_tmp, shaped_mp3)

    for f_tmp in [clean_voice_tmp, sfx_tmp]:
        try:
            if os.path.exists(f_tmp):
                os.remove(f_tmp)
        except Exception:
            pass


def _master_scenes_with_cinematic_bg_ffmpeg(scene_mp3s: List[str], final_mp3: str, dna: Dict[str, Any]) -> None:
    work_dir = os.path.dirname(os.path.abspath(final_mp3))
    concat_txt = os.path.join(work_dir, "_voice_concat.txt")
    raw_voice_master = os.path.join(work_dir, "_voice_only_master.mp3")

    with open(concat_txt, "w", encoding="utf-8") as f:
        for p in scene_mp3s:
            safe_p = os.path.abspath(p).replace("\\", "/")
            f.write(f"file '{safe_p}'\n")

    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_txt, "-c:a", "libmp3lame", "-b:a", "192k", raw_voice_master],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
    )

    dur_sec = max(_get_audio_duration_ms(raw_voice_master) / 1000.0, 1.0)
    bg_bed = os.path.join(work_dir, "_ambient_drone_bed.mp3")
    fade_out_start = max(0.5, dur_sec - 1.2)

    drone_lavfi = (
        f"anoisesrc=d={dur_sec:.2f}:c=pink:r=24000:a=0.028,"
        f"lowpass=f=120,"
        f"afade=t=in:st=0:d=0.4,"
        f"afade=t=out:st={fade_out_start:.2f}:d=1.2,"
        f"volume=0.20"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", drone_lavfi, "-c:a", "libmp3lame", "-b:a", "128k", bg_bed],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
    )

    mix_cmd = [
        "ffmpeg", "-y",
        "-i", raw_voice_master,
        "-i", bg_bed,
        "-filter_complex",
        "[0:a]highpass=f=75,equalizer=f=165:width_type=o:width=1.2:g=2.2,equalizer=f=3200:width_type=o:width=1.8:g=1.8,volume=1.15[v];"
        "[1:a]volume=0.18[bg];"
        "[v][bg]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[out]",
        "-map", "[out]",
        "-c:a", "libmp3lame", "-b:a", "192k",
        final_mp3
    ]
    subprocess.run(mix_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    for tmp in [concat_txt, raw_voice_master, bg_bed] + scene_mp3s:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass


def _audit_and_fix_audio_duration_self_critic(
    mp3_path: str,
    dna: Dict[str, Any],
    num_scenes: int
) -> Tuple[float, float]:
    raw_ms = _get_audio_duration_ms(mp3_path)
    actual_sec = raw_ms / 1000.0

    if num_scenes < 3 or actual_sec < 15.0:
        return raw_ms, 1.0

    bounds = dna.get("script_engine", {}).get("target_duration_bounds_sec", [46.0, 54.0])
    min_sec, max_sec = float(bounds[0]), float(bounds[1])

    if min_sec <= actual_sec <= max_sec:
        print(f"  [Audio Self-Critic] PASS: {actual_sec:.2f}s is strictly inside target [{min_sec}s - {max_sec}s] (Zero atempo warp!).")
        return raw_ms, 1.0

    target_sec = (min_sec + 1.0) if actual_sec < min_sec else (max_sec - 1.0)
    atempo_factor = max(0.90, min(1.08, actual_sec / target_sec))
    corrected_mp3 = mp3_path.replace(".mp3", "_tempo_fixed.mp3")

    print(f"  [Audio Self-Critic] GENTLE ADJUST: {actual_sec:.2f}s -> applying subtle atempo={atempo_factor:.3f}")
    subprocess.run(
        ["ffmpeg", "-y", "-i", mp3_path, "-af", f"atempo={atempo_factor:.3f}", "-c:a", "libmp3lame", "-b:a", "192k", corrected_mp3],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
    )
    os.replace(corrected_mp3, mp3_path)

    final_ms = _get_audio_duration_ms(mp3_path)
    tempo_scale_ratio = final_ms / max(raw_ms, 1.0)
    print(f"  [Audio Self-Critic] FIXED: New Master Audio Duration = {final_ms / 1000.0:.2f}s")
    return final_ms, tempo_scale_ratio


def _apply_mixed_script_formatting(text: str) -> str:
    out = text.replace("—", "")
    for dev_phrase, eng_phrase in DEVANAGARI_TO_ENGLISH_SUB_MAP.items():
        out = out.replace(dev_phrase, eng_phrase)
    return re.sub(r"\s+", " ", out).strip()


def _ms_to_srt_timestamp(ms: float) -> str:
    total_ms = max(0, int(round(ms)))
    hours = total_ms // 3600000
    rem = total_ms % 3600000
    minutes = rem // 60000
    rem %= 60000
    seconds = rem // 1000
    millis = rem % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def _group_events_without_orphans(
    events: List[Dict[str, Any]],
    max_words: int = 4
) -> List[List[Dict[str, Any]]]:
    compound_pairs = {
        ("पार्ट", "टू"), ("पार्ट", "2"), ("डार्क", "पैटर्न"),
        ("कॉल", "फॉरवर्डिंग"), ("बैटरी", "टेलीमेट्री"), ("डिकॉय", "प्राइसिंग"),
        ("क्रेडिट", "कार्ड")
    }
    merged_events: List[Dict[str, Any]] = []
    skip_next = False
    for idx_e, ev in enumerate(events):
        if skip_next:
            skip_next = False
            continue
        if idx_e + 1 < len(events) and not ev.get("force_break"):
            w1 = re.sub(r"[^\w]", "", ev["text"])
            w2 = re.sub(r"[^\w]", "", events[idx_e + 1]["text"])
            if (w1, w2) in compound_pairs:
                nxt = events[idx_e + 1]
                merged_events.append({
                    "text": f"{ev['text']} {nxt['text']}",
                    "offset_ms": ev["offset_ms"],
                    "duration_ms": (nxt["offset_ms"] + nxt["duration_ms"]) - ev["offset_ms"],
                    "force_break": nxt.get("force_break", False)
                })
                skip_next = True
                continue
        merged_events.append(ev)
    events = merged_events

    clauses: List[List[Dict[str, Any]]] = []
    curr_clause: List[Dict[str, Any]] = []

    for i, ev in enumerate(events):
        curr_clause.append(ev)
        word_txt = ev["text"].strip()
        ends_punct = any(p in word_txt for p in ["।", "?", "!", "—", ","])
        is_forced = bool(ev.get("force_break", False))
        next_gap_ms = 0.0
        if i + 1 < len(events):
            next_gap_ms = events[i + 1]["offset_ms"] - (ev["offset_ms"] + ev["duration_ms"])

        if is_forced or ends_punct or next_gap_ms > 180.0:
            clauses.append(curr_clause)
            curr_clause = []

    if curr_clause:
        clauses.append(curr_clause)

    final_chunks: List[List[Dict[str, Any]]] = []
    for clause in clauses:
        n = len(clause)
        if n <= max_words:
            final_chunks.append(clause)
        else:
            temp = [clause[i:i + max_words] for i in range(0, n, max_words)]
            if len(temp) >= 2 and len(temp[-1]) == 1:
                temp[-2].extend(temp[-1])
                temp.pop()
            final_chunks.extend(temp)

    return final_chunks


def _build_mixed_script_srt(
    scene_blocks: List[Dict[str, Any]],
    srt_path: str,
    max_words_per_caption: int = 4
) -> None:
    srt_entries: List[str] = []
    idx = 1

    for block in scene_blocks:
        events = block.get("events", [])
        if events:
            smart_chunks = _group_events_without_orphans(events, max_words=max_words_per_caption)
            for c_i, chunk in enumerate(smart_chunks):
                start_ms = chunk[0]["offset_ms"]
                end_ms = chunk[-1]["offset_ms"] + max(chunk[-1]["duration_ms"], 160.0)
                if c_i + 1 < len(smart_chunks):
                    next_start = smart_chunks[c_i + 1][0]["offset_ms"]
                    end_ms = min(end_ms, max(start_ms + 120.0, next_start - 15.0))
                raw_line = " ".join(ev["text"] for ev in chunk)
                clean_line = _apply_mixed_script_formatting(raw_line)
                if clean_line:
                    srt_entries.append(
                        f"{idx}\n{_ms_to_srt_timestamp(start_ms)} --> {_ms_to_srt_timestamp(end_ms)}\n{clean_line}\n"
                    )
                    idx += 1
        else:
            words = _apply_mixed_script_formatting(block["text"]).split()
            if not words:
                continue
            chunks = [words[i:i + max_words_per_caption] for i in range(0, len(words), max_words_per_caption)]
            if len(chunks) >= 2 and len(chunks[-1]) == 1:
                chunks[-2].extend(chunks[-1])
                chunks.pop()
            step_ms = block["duration_ms"] / len(chunks)
            for c_idx, c_words in enumerate(chunks):
                s_ms = block["start_ms"] + (c_idx * step_ms)
                e_ms = s_ms + step_ms
                srt_entries.append(
                    f"{idx}\n{_ms_to_srt_timestamp(s_ms)} --> {_ms_to_srt_timestamp(e_ms)}\n{' '.join(c_words)}\n"
                )
                idx += 1

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_entries))


async def _synthesize_emotional_documentary_async(
    beats: List[str],
    mp3_path: str,
    srt_path: str
) -> None:
    dna = load_trend_dna()
    voice_name = INDIAN_VOICES.get(VOICE_GENDER, "hi-IN-MadhurNeural")
    work_dir = os.path.dirname(os.path.abspath(mp3_path))
    os.makedirs(work_dir, exist_ok=True)

    # Allow Trend DNA to override pause timings within the 200-300ms range if trained
    audio_cfg = dna.get("audio_engine", {})
    active_prof = audio_cfg.get("active_cadence_profile", "high_tension_documentary")
    prof_cfg = audio_cfg.get("cadence_profiles", {}).get(active_prof, {})
    clause_pause_ms = int(prof_cfg.get("mid_clause_pause_ms", MID_CLAUSE_PAUSE_MS))
    clause_pause_ms = max(180, min(320, clause_pause_ms))
    scene_breath_ms = int(prof_cfg.get("inter_scene_breath_ms", INTER_SCENE_BREATH_MS))
    scene_breath_ms = max(150, min(300, scene_breath_ms))

    shaped_mp3s: List[str] = []
    scene_blocks: List[Dict[str, Any]] = []
    cumulative_ms = 0.0

    print(
        f"Synthesizing Clause-Locked Voiceover via {voice_name} "
        f"({clause_pause_ms}ms Hinge Pause at ','/'—' + {scene_breath_ms}ms Scene Breath)..."
    )

    for idx, beat_text in enumerate(beats, 1):
        tts_text = _normalize_hinge_punctuation(beat_text)
        prof = SCENE_EMOTION_PROFILES.get(idx, SCENE_EMOTION_PROFILES[3])
        sub_clauses = _split_scene_into_setup_and_reveal(tts_text)

        raw_scene_mp3 = os.path.join(work_dir, f"_raw_sc_{idx:02d}.mp3")
        shaped_scene_mp3 = os.path.join(work_dir, f"_shaped_sc_{idx:02d}.mp3")

        print(
            f"  -> Scene {idx} [{prof['name']}]: "
            f"{len(sub_clauses)} clause(s) (Setup:{prof['setup_pitch']}/{prof['setup_rate']} -> Reveal:{prof['reveal_pitch']}/{prof['reveal_rate']})"
        )

        trimmed_clause_files: List[str] = []
        raw_events: List[Dict[str, Any]] = []
        clause_cursor_ms = 0.0
        has_two_clauses = len(sub_clauses) > 1

        for c_idx, clause_str in enumerate(sub_clauses):
            c_pitch = prof["setup_pitch"] if c_idx == 0 else prof["reveal_pitch"]
            c_rate = prof["setup_rate"] if c_idx == 0 else prof["reveal_rate"]
            c_raw_mp3 = os.path.join(work_dir, f"_sc_{idx:02d}_cl_{c_idx}_raw.mp3")
            c_trim_mp3 = os.path.join(work_dir, f"_sc_{idx:02d}_cl_{c_idx}_trim.mp3")

            communicate = edge_tts.Communicate(
                text=clause_str,
                voice=voice_name,
                pitch=c_pitch,
                rate=c_rate
            )
            c_events: List[Dict[str, Any]] = []
            with open(c_raw_mp3, "wb") as f:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        f.write(chunk["data"])
                    elif chunk["type"] == "WordBoundary":
                        c_events.append({
                            "text": chunk["text"],
                            "rel_offset_ms": chunk["offset"] / 10000.0,
                            "duration_ms": chunk["duration"] / 10000.0
                        })

            _trim_sub_clause_ffmpeg(
                c_raw_mp3,
                c_trim_mp3,
                is_first_clause=(c_idx == 0),
                has_second_clause=has_two_clauses,
                clause_pause_ms=clause_pause_ms
            )
            c_trim_dur_ms = max(_get_audio_duration_ms(c_trim_mp3), 1.0)

            if c_events:
                first_off = c_events[0]["rel_offset_ms"]
                raw_span = max((c_events[-1]["rel_offset_ms"] + c_events[-1]["duration_ms"]) - first_off, 1.0)
                tail_pad_ms = float(clause_pause_ms) if (c_idx == 0 and has_two_clauses) else 20.0
                active_voice_ms = max(c_trim_dur_ms - tail_pad_ms, raw_span * 0.75)
                c_scale = active_voice_ms / raw_span

                for ev_i, ev in enumerate(c_events):
                    is_last_in_clause_1 = (c_idx == 0 and has_two_clauses and ev_i == len(c_events) - 1)
                    raw_events.append({
                        "text": ev["text"],
                        "rel_offset_ms": clause_cursor_ms + ((ev["rel_offset_ms"] - first_off) * c_scale),
                        "duration_ms": ev["duration_ms"] * c_scale,
                        "force_break": is_last_in_clause_1
                    })

            clause_cursor_ms += c_trim_dur_ms
            trimmed_clause_files.append(c_trim_mp3)
            if os.path.exists(c_raw_mp3):
                try:
                    os.remove(c_raw_mp3)
                except Exception:
                    pass

        if len(trimmed_clause_files) == 1:
            os.replace(trimmed_clause_files[0], raw_scene_mp3)
        else:
            cl_list_txt = os.path.join(work_dir, f"_cl_list_{idx}.txt")
            with open(cl_list_txt, "w", encoding="utf-8") as cf:
                for cp in trimmed_clause_files:
                    cf.write(f"file '{os.path.abspath(cp).replace(chr(92), '/')}'\n")
            subprocess.run(
                ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", cl_list_txt, "-c:a", "libmp3lame", "-b:a", "192k", raw_scene_mp3],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
            )
            for tmp_c in trimmed_clause_files + [cl_list_txt]:
                try:
                    if os.path.exists(tmp_c):
                        os.remove(tmp_c)
                except Exception:
                    pass

        raw_dur_ms = max(_get_audio_duration_ms(raw_scene_mp3), 1.0)
        _shape_scene_with_cinematic_whoosh_and_breath(raw_scene_mp3, shaped_scene_mp3, idx, scene_breath_ms=scene_breath_ms)
        shaped_dur_ms = _get_audio_duration_ms(shaped_scene_mp3)

        spoken_span_ms = max(shaped_dur_ms - float(scene_breath_ms), raw_dur_ms * 0.88)
        scale_ratio = spoken_span_ms / raw_dur_ms

        scaled_events = []
        for ev in raw_events:
            scaled_events.append({
                "text": ev["text"],
                "offset_ms": cumulative_ms + (ev["rel_offset_ms"] * scale_ratio),
                "duration_ms": ev["duration_ms"] * scale_ratio,
                "force_break": ev.get("force_break", False)
            })

        scene_blocks.append({
            "text": tts_text,
            "start_ms": cumulative_ms,
            "duration_ms": shaped_dur_ms,
            "events": scaled_events
        })

        cumulative_ms += shaped_dur_ms
        shaped_mp3s.append(shaped_scene_mp3)

        try:
            if os.path.exists(raw_scene_mp3):
                os.remove(raw_scene_mp3)
        except Exception:
            pass

    _master_scenes_with_cinematic_bg_ffmpeg(shaped_mp3s, mp3_path, dna)
    final_duration_ms, tempo_scale = _audit_and_fix_audio_duration_self_critic(mp3_path, dna, len(beats))

    if tempo_scale != 1.0:
        for block in scene_blocks:
            block["start_ms"] *= tempo_scale
            block["duration_ms"] *= tempo_scale
            for ev in block.get("events", []):
                ev["offset_ms"] *= tempo_scale
                ev["duration_ms"] *= tempo_scale

    meta_path = mp3_path.replace(".mp3", "_scenes.json")
    scene_durations_sec = [round(b["duration_ms"] / 1000.0, 3) for b in scene_blocks]
    with open(meta_path, "w", encoding="utf-8") as mf:
        json.dump(
            {
                "scene_durations_sec": scene_durations_sec,
                "mid_clause_hinge_gap_ms": clause_pause_ms,
                "inter_scene_breath_ms": scene_breath_ms,
                "total_ms": round(final_duration_ms, 1)
            },
            mf,
            indent=2
        )
    print(f"  [Beat-Lock Export] Saved exact {len(scene_durations_sec)}-scene durations {scene_durations_sec}s -> {os.path.basename(meta_path)}")

    asm_cfg = dna.get("assembly_engine", {})
    active_edit = asm_cfg.get("active_edit_profile", "viral_center_yellow")
    burst_limit = int(asm_cfg.get("edit_profiles", {}).get(active_edit, {}).get("subtitle_burst_words", 4))

    _build_mixed_script_srt(scene_blocks, srt_path, max_words_per_caption=burst_limit)


def generate_voiceover(
    text: str,
    output_base_path: str,
    scenes: Optional[List[Dict[str, Any]]] = None
) -> Tuple[str, str]:
    base = output_base_path[:-4] if output_base_path.endswith(".mp3") else output_base_path
    mp3_path = f"{base}.mp3"
    srt_path = f"{base}.srt"
    os.makedirs(os.path.dirname(os.path.abspath(mp3_path)), exist_ok=True)

    if scenes and isinstance(scenes, list):
        beats = [
            s.get("narration_hinglish") or s.get("narration") or ""
            for s in scenes
            if (s.get("narration_hinglish") or s.get("narration"))
        ]
    else:
        parts = [p.strip() for p in re.split(r"\n+", text.strip()) if p.strip()]
        beats = parts if parts else [text.strip()]

    asyncio.run(_synthesize_emotional_documentary_async(beats, mp3_path, srt_path))
    return mp3_path, srt_path