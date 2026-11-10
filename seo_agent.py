import os
import json
from typing import Dict, Any

try:
    from agents.trend_agent import load_trend_dna
except ImportError:
    def load_trend_dna() -> Dict[str, Any]:
        return {}

try:
    from services.llm_brain import call_smart_llm_json
except ImportError:
    def call_smart_llm_json(sys_p: str, usr_p: str, temperature: float = 0.35, cloud_only: bool = False) -> Dict[str, Any]:
        return {}

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STORAGE_DIR = os.path.join(PROJECT_ROOT, "storage")


def generate_and_critique_seo_metadata(script_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates a high-CTR bilingual YouTube Shorts Title (<70 chars),
    an algorithm-friendly description, tags, and a Pinned Comment
    designed to convert the Scene 6 cliffhanger into 'PART 2' comments.
    """
    dna = load_trend_dna()
    topic = script_data.get("topic", "Hidden Digital Trap Exposed")
    scenes = script_data.get("scenes", [])
    cliffhanger = scenes[-1].get("narration_hinglish", "") if scenes else ""

    sys_prompt = """You are a YouTube Shorts Viral Packaging & CTR Specialist for Indian Dark Psychology and Scam Expose channels.
Return ONLY valid JSON with:
- "title": High-curiosity bilingual English + Hindi title under 68 characters ending with ⚠️ #shorts
- "pinned_comment": Engaging Hindi/Hinglish pinned comment asking viewers to comment 'PART 2' to unlock the cliffhanger topic
- "description": 3-line SEO description with 5 niche hashtags
- "tags": list of 8 high-volume search tags"""

    user_prompt = json.dumps({
        "topic": topic,
        "scene_6_cliffhanger": cliffhanger
    }, ensure_ascii=False)

    res = call_smart_llm_json(sys_prompt, user_prompt, temperature=0.4, cloud_only=True)

    short_topic = topic.split("—")[0].strip() if "—" in topic else topic[:38].strip()
    default_title = f"{short_topic} ⚠️ [सावधान] #shorts #scam"
    title = str(res.get("title") or default_title).strip()
    if "#shorts" not in title.lower():
        title = f"{title[:58]} #shorts"

    pinned_comment = str(
        res.get("pinned_comment")
        or f"📌 {cliffhanger} 👇 नीचे 'PART 2' कमेंट करें, अगला वीडियो इसी पर आएगा!"
    ).strip()

    seo_payload = {
        "video_id": script_data.get("video_id", "EXP_001"),
        "title": title,
        "pinned_comment": pinned_comment,
        "description": str(res.get("description") or f"{topic}\n\n{pinned_comment}\n\n#shorts #darkpsychology #scamalert #cybersecurity #india"),
        "tags": res.get("tags") or ["shorts", "dark psychology hindi", "scam expose", "cyber security india", "hidden charges"]
    }

    seo_path = os.path.join(STORAGE_DIR, f"{seo_payload['video_id']}_seo.json")
    os.makedirs(STORAGE_DIR, exist_ok=True)
    with open(seo_path, "w", encoding="utf-8") as f:
        json.dump(seo_payload, f, ensure_ascii=False, indent=2)

    print(f"  [SEO Self-Critic] PASS: Title='{seo_payload['title']}' | Saved -> {os.path.basename(seo_path)}")
    return seo_payload