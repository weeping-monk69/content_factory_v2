import os
import re
import json
import random
from datetime import datetime
from typing import List, Dict, Any, Tuple

try:
    from agents.trend_agent import load_trend_dna
except ImportError:
    try:
        from trend_agent import load_trend_dna
    except ImportError:
        def load_trend_dna() -> Dict[str, Any]:
            return {}

from services.llm_brain import (
    call_smart_llm_json,
    run_honest_critic_and_auto_fix,
    _get_api_keys
)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STORAGE_DIR = os.path.join(PROJECT_ROOT, "storage")
HISTORY_PATH = os.path.join(STORAGE_DIR, "script_history.json")
ANTI_REPEAT_LEDGER_PATH = os.path.join(STORAGE_DIR, "anti_repeat_ledger.json")

PERMANENTLY_BANNED_TOPIC_KEYWORDS = [
    "battery drop", "14% बैटरी", "कैब ऐप्स का 14%",
    "clipboard", "कॉपी किया हुआ पासवर्ड",
    "401#", "ussd", "कॉल फॉरवर्डिंग",
    "roach motel", "सब्सक्रिप्शन कैंसिल",
    "decoy pricing", "डिकॉय प्राइसिंग"
]

# ==============================================================================
# FULL-SPECTRUM 5-PILLAR DARK PSYCHOLOGY & FORENSIC SEED MATRIX
# ==============================================================================
VIRAL_SEED_CATEGORIES: List[Dict[str, str]] = [
    # PILLAR 1: INTERPERSONAL MANIPULATION & MIND GAMES
    {
        "id": "psych_intermittent_reinforcement",
        "vector": "mind_control",
        "pillar": "Dark Psychology | Mind Manipulation",
        "visual_mode": "human_neural_3d",
        "seed_hint": "Intermittent Reinforcement: Why toxic manipulators alternate between intense praise and sudden cold distance to hijack your brain's dopamine system like a casino slot machine"
    },
    {
        "id": "psych_darvo_flip",
        "vector": "mind_control",
        "pillar": "Dark Psychology | Narcissist Tactics",
        "visual_mode": "human_neural_3d",
        "seed_hint": "The DARVO Manipulation Trick: How clever manipulators instantly flip an argument when caught lying so YOU end up apologizing to THEM within 3 minutes"
    },
    {
        "id": "psych_silent_treatment_pain",
        "vector": "mind_control",
        "pillar": "Dark Psychology | Emotional Warfare",
        "visual_mode": "human_neural_3d",
        "seed_hint": "Weaponized Silent Treatment: Why deliberately ignoring someone activates the Anterior Cingulate Cortex (physical pain center) in their brain to force total submission"
    },
    {
        "id": "psych_double_bind_illusion",
        "vector": "friction_asymmetry",
        "pillar": "Dark Psychology | Choice Hijacking",
        "visual_mode": "human_neural_3d",
        "seed_hint": "The Double-Bind False Choice Trap: How master manipulators offer you two options that make you feel in control while both secretly lock you into their exact goal"
    },

    # PILLAR 2: LIE DETECTION, BODY LANGUAGE & MICRO-EXPRESSIONS
    {
        "id": "lie_blink_rate_spike",
        "vector": "hardware_telemetry",
        "pillar": "Dark Psychology | Forensic Lie Detection",
        "visual_mode": "human_neural_3d",
        "seed_hint": "Forensic Eye-Blink Lie Detection: Why a liar's eyes freeze completely still while speaking a lie, followed by a 6x rapid blink burst in the 3 seconds right after"
    },
    {
        "id": "lie_feet_direction_leak",
        "vector": "hardware_telemetry",
        "pillar": "Dark Psychology | Subconscious Body Language",
        "visual_mode": "human_neural_3d",
        "seed_hint": "The Limbic Foot-Pointing Tell: Why a person can fake a warm smile with their face, but their feet subconsciously rotate toward the exit door the moment they want to escape you"
    },
    {
        "id": "lie_detail_overload_reverse",
        "vector": "authority_panic",
        "pillar": "Dark Psychology | Interrogation Secrets",
        "visual_mode": "human_neural_3d",
        "seed_hint": "The Reverse-Order Interrogation Trick: Why FBI investigators ask suspects to tell their story backward from the end—causing rehearsed lies to collapse in 20 seconds"
    },

    # PILLAR 3: FORBIDDEN PERSUASION, POWER & NEGOTIATION
    {
        "id": "power_four_second_silence",
        "vector": "authority_panic",
        "pillar": "Dark Psychology | Power Dynamics",
        "visual_mode": "human_neural_3d",
        "seed_hint": "The 4-Second Dead Silence Tactic: Why staring calmly in total silence for 4 seconds after an insult or lowball offer triggers acute social panic and forces the other person to fold"
    },
    {
        "id": "power_ben_franklin_favor",
        "vector": "hidden_arbitrage",
        "pillar": "Dark Psychology | Subconscious Persuasion",
        "visual_mode": "human_neural_3d",
        "seed_hint": "The Benjamin Franklin Cognitive Dissonance Hack: Why asking a cold rival for a tiny, effortless favor rewires their brain to justify liking and trusting you"
    },
    {
        "id": "power_fbi_3word_mirror",
        "vector": "mind_control",
        "pillar": "Dark Psychology | Hostage Negotiation",
        "visual_mode": "human_neural_3d",
        "seed_hint": "FBI 3-Word Mirroring: How repeating just the last three words someone says with an upward inflection tricks them into revealing their deepest hidden motive without realizing it"
    },

    # PILLAR 4: SUBCONSCIOUS BRAIN BUGS & MASS SOCIAL ENGINEERING
    {
        "id": "bias_1am_prefrontal_fatigue",
        "vector": "hardware_telemetry",
        "pillar": "Dark Psychology | Brain Exploitation",
        "visual_mode": "human_neural_3d",
        "seed_hint": "1 AM Prefrontal Cortex Shutdown: How apps and late-night marketers exploit the 40% drop in your brain's logical impulse control after midnight to trigger regret purchases and over-sharing"
    },
    {
        "id": "bias_sunk_cost_trap",
        "vector": "friction_asymmetry",
        "pillar": "Dark Psychology | Cognitive Traps",
        "visual_mode": "human_neural_3d",
        "seed_hint": "The Sunk-Cost Dopamine Prison: Why the human brain prefers losing another 5 years in a toxic relationship or bad bet rather than admitting a past mistake"
    },

    # PILLAR 5: CYBER SCAMS & PREDATORY CORPORATE TRAPS
    {
        "id": "seed_upi_soundbox",
        "vector": "authority_panic",
        "pillar": "Digital Scam Expose | Payment Fraud",
        "visual_mode": "device_forensic_3d",
        "seed_hint": "Fake kirana store UPI soundbox voice spoof app announcing payment received without real bank settlement"
    },
    {
        "id": "seed_flight_cookies",
        "vector": "hidden_arbitrage",
        "pillar": "Predatory Money Habits | Algorithmic Pricing",
        "visual_mode": "device_forensic_3d",
        "seed_hint": "Flight & hotel booking apps tracking repeat search cookies and Wi-Fi tier to inflate ticket fares by ₹1,200 in 3 minutes"
    },
    {
        "id": "seed_telecom_28day",
        "vector": "friction_asymmetry",
        "pillar": "Predatory Money Habits | Hidden Arbitrage",
        "visual_mode": "device_forensic_3d",
        "seed_hint": "Telecom 28-day recharge cycle stealth math forcing 13 monthly recharges per year instead of 12"
    },
    {
        "id": "seed_wifi_bssid",
        "vector": "hardware_telemetry",
        "pillar": "Dark Psychology | Silent Hardware Betrayal",
        "visual_mode": "device_forensic_3d",
        "seed_hint": "Smartphone apps reading nearby Wi-Fi router MAC/BSSID addresses to pinpoint your exact apartment floor even when GPS is turned OFF"
    },
    {
        "id": "seed_cc_min_due",
        "vector": "hidden_arbitrage",
        "pillar": "Predatory Money Habits | Banking Traps",
        "visual_mode": "device_forensic_3d",
        "seed_hint": "Credit card Minimum Due 5% payment trap silently voiding the 45-day interest-free grace period and charging 42% APR from day one"
    }
]

OFFLINE_FRESH_BLUEPRINTS: List[Dict[str, Any]] = [
    {
        "combo_key": "offline_psych_four_second_silence",
        "collision_vector_id": "authority_panic",
        "domain": "Dark Psychology & Power Dynamics",
        "pillar": "Dark Psychology | Power Dynamics",
        "topic": "The 4-Second Silence Rule — बहस और नेगोशिएशन जीतने का डार्क साइकोलॉजी हथियार",
        "angle": {
            "trigger": "कोई बातचीत में आपकी बात काटता है या आपका मज़ाक उड़ाता है",
            "focus": "फोर-सेकंड साइलेंस",
            "mechanism": "तुरंत सफाई देने के बजाय, उस इंसान की आंखों में शांत देखकर पूरे चार सेकंड तक बिल्कुल चुप हो जाइए।",
            "metric": "बिहेवियरल साइकोलॉजी के मुताबिक सिर्फ चार सेकंड का सन्नाटा, सामने वाले के दिमाग में अस्सी प्रतिशत सोशल एंग्जाइटी पैदा कर देता है।",
            "twist": "असली खेल यह है—इंसानी दिमाग इस अजीब खामोशी को बर्दाश्त नहीं कर पाता, और वह खुद घबराकर अपनी गलती सुधारने लगता है।",
            "seekh": "जब भी कोई अनुचित शर्त रखे, तो तुरंत बोलने के बजाय चार सेकंड का शांत पॉज़ लेकर सामने वाले का आत्मविश्वास तोड़ दें",
            "cliffhanger": "लेकिन कोई इंसान झूठ बोलते वक्त अपनी पलकें किस खास पैटर्न में झपकाता है? अभी पार्ट टू कमेंट करें!"
        },
        "visuals": [
            "Close-up 3D cinematic shot of two translucent human figures facing each other across a dark obsidian table as one speaks aggressively with chaotic red soundwaves while the other remains dead calm in glowing cyan light, vertical 9:16",
            "Macro 3D cutaway of a calm human eye locking gaze as a glowing 4-second digital timer ring freezes the room in deep volumetric blue silence",
            "3D X-ray view of the aggressor's brain where the amygdala lights up with pulsing crimson anxiety waves as their confidence meter drops by 80 percent",
            "Cinematic 3D visualization of golden power puppet strings reversing direction from the speaker to the silent listener across the dark table",
            "Crisp 3D close-up of a composed silhouette surrounded by an emerald psychological aura shield while the opponent steps backward in submission",
            "Suspenseful macro 3D close-up of a human eye with a dilating pupil and a glowing red lie-detector waveform reflecting off the cornea"
        ]
    },
    {
        "combo_key": "offline_psych_intermittent_reinforcement",
        "collision_vector_id": "mind_control",
        "domain": "Neuro-Manipulation & Dopamine Traps",
        "pillar": "Dark Psychology | Mind Manipulation",
        "topic": "Intermittent Reinforcement — टॉक्सिक लोग आपके दिमाग को अपना आदी कैसे बनाते हैं",
        "angle": {
            "trigger": "कोई इंसान कभी आपको बहुत प्यार देता है और अचानक अनदेखा करने लगता है",
            "focus": "इंटरमिटेंट रिइंफोर्समेंट",
            "mechanism": "यह कोई इत्तेफाक नहीं बल्कि एक सोचा-समझा मनोवैज्ञानिक जाल है, जिसे कैसिनो की स्लॉट मशीन की तरह डिज़ाइन किया गया है।",
            "metric": "न्यूरोसाइंस डेटा के अनुसार अनिश्चित इनाम मिलने पर, आपके दिमाग में सामान्य से दोगुना ज़्यादा डोपामाइन रिलीज़ होता है।",
            "twist": "असली खेल यह है—जब वह इंसान अचानक बात बंद करता है, तो आपका दिमाग उसकी एक तारीफ पाने के लिए तड़पने लगता है।",
            "seekh": "अगर कोई बार-बार गर्म और ठंडा व्यवहार करे, तो तुरंत इमोशनल रिएक्शन देना बंद करें और अपना ध्यान पूरी तरह हटा लें",
            "cliffhanger": "लेकिन बातचीत में सिर्फ आखिरी तीन शब्द दोहराकर, आप किसी का छुपा हुआ सच कैसे उगलवा सकते हैं? अभी पार्ट टू कमेंट करें!"
        },
        "visuals": [
            "Close-up 3D cinematic render of a translucent human silhouette holding a glowing smartphone as the heart-rate aura shifts violently from warm gold to freezing icy blue, vertical 9:16",
            "3D forensic cutaway of a human brain connected by glowing red neural cables to a spinning dark-gold casino slot machine inside an obsidian studio",
            "Split-screen 3D neural comparison showing steady normal dopamine drops versus a massive 200 percent crimson dopamine spike triggered by unpredictable attention",
            "Macro 3D view of glowing golden puppet strings tightening around a translucent human mind whenever a distant figure turns their back",
            "Crisp 3D visualization of golden glowing scissors severing the manipulative neural cords as an emerald mental shield forms around the brain",
            "Mysterious 3D close-up of two shadowy figures in conversation where three glowing cyan sound rings echo back and unlock a hidden red vault in the speaker's mind"
        ]
    }
]


def _clean_and_normalize_hinglish(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    cleaned = cleaned.replace(" ,", ",").replace(" !", "!").replace(" ?", "?")
    cleaned = cleaned.replace("पार्ट 2", "पार्ट टू").replace("PART 2", "पार्ट टू")
    return cleaned


def _load_json_list(path: str) -> List[Dict[str, Any]]:
    os.makedirs(STORAGE_DIR, exist_ok=True)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                return []
            clean_list = []
            for item in data:
                if isinstance(item, dict):
                    clean_list.append(item)
                elif isinstance(item, str):
                    clean_list.append({"topic": item, "combo_key": item, "seed_id": item})
            return clean_list
    except Exception:
        return []


def _save_json_list(path: str, data: List[Dict[str, Any]]) -> None:
    os.makedirs(STORAGE_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data[-250:], f, ensure_ascii=False, indent=2)


def _is_topic_banned_or_repeated(topic: str, combo_key: str, past_topics: List[str], past_keys: set) -> bool:
    t_low = topic.lower().strip()
    if not t_low:
        return True
    if combo_key in past_keys:
        return True
    for banned in PERMANENTLY_BANNED_TOPIC_KEYWORDS:
        if banned.lower() in t_low:
            return True
    for pt in past_topics:
        pt_low = pt.lower().strip()
        if t_low == pt_low:
            return True
        if "—" in t_low and "—" in pt_low:
            if t_low.split("—")[0].strip() == pt_low.split("—")[0].strip():
                return True
    return False


class CohesiveTopicEngine:
    @staticmethod
    def select_cohesive_blueprint(history: List[Dict[str, Any]], dna: Dict[str, Any]) -> Dict[str, Any]:
        ledger = _load_json_list(ANTI_REPEAT_LEDGER_PATH)

        past_topics = (
            [h.get("topic", "") for h in history if isinstance(h, dict) and h.get("topic")]
            + [l.get("topic", "") for l in ledger if isinstance(l, dict) and l.get("topic")]
        )
        past_keys = (
            {h.get("combo_key", "") for h in history if isinstance(h, dict) and h.get("combo_key")}
            | {l.get("combo_key", "") for l in ledger if isinstance(l, dict) and l.get("combo_key")}
        )
        past_seed_ids = (
            {h.get("seed_id", "") for h in history if isinstance(h, dict) and h.get("seed_id")}
            | {l.get("seed_id", "") for l in ledger if isinstance(l, dict) and l.get("seed_id")}
        )

        # Ensure we alternate naturally between Deep Human Dark Psychology and Cyber/Financial Traps
        last_pillar = history[-1].get("pillar", "") if history and isinstance(history[-1], dict) else ""
        unused_seeds = [s for s in VIRAL_SEED_CATEGORIES if s["id"] not in past_seed_ids]
        if not unused_seeds:
            unused_seeds = list(VIRAL_SEED_CATEGORIES)
            random.shuffle(unused_seeds)

        # Prioritize human dark psychology seeds if the last run was a financial/tech scam (and vice versa)
        if "Scam" in last_pillar or "Money" in last_pillar:
            psych_seeds = [s for s in unused_seeds if s.get("visual_mode") == "human_neural_3d"]
            if psych_seeds:
                unused_seeds = psych_seeds

        groq_key, gemini_key = _get_api_keys()
        if groq_key or gemini_key:
            for attempt in range(3):
                chosen_seed = random.choice(unused_seeds)
                print(f"  [Unique Topic Engine] Inventing Cloud LLM blueprint for Pillar: '{chosen_seed['pillar']}' ({chosen_seed['id']})...")
                fresh_bp = CohesiveTopicEngine._invent_fresh_blueprint_via_llm(
                    chosen_seed,
                    past_topics,
                    dna
                )
                if fresh_bp and not _is_topic_banned_or_repeated(
                    fresh_bp.get("topic", ""), fresh_bp.get("combo_key", ""), past_topics, past_keys
                ):
                    fresh_bp["seed_id"] = chosen_seed["id"]
                    ledger.append({
                        "timestamp": datetime.now().isoformat(),
                        "seed_id": chosen_seed["id"],
                        "combo_key": fresh_bp["combo_key"],
                        "topic": fresh_bp["topic"]
                    })
                    _save_json_list(ANTI_REPEAT_LEDGER_PATH, ledger)
                    print(f"  [Unique Topic Engine] SUCCESS — Invented 100% Fresh Viral Topic: {fresh_bp['topic']}")
                    return fresh_bp

        unused_offline = [
            b for b in OFFLINE_FRESH_BLUEPRINTS
            if not _is_topic_banned_or_repeated(b["topic"], b["combo_key"], past_topics, past_keys)
        ]
        if not unused_offline:
            unused_offline = list(OFFLINE_FRESH_BLUEPRINTS)
            random.shuffle(unused_offline)

        chosen_off = json.loads(json.dumps(unused_offline[0]))
        chosen_off["seed_id"] = chosen_off["combo_key"]
        ledger.append({
            "timestamp": datetime.now().isoformat(),
            "seed_id": chosen_off["combo_key"],
            "combo_key": chosen_off["combo_key"],
            "topic": chosen_off["topic"]
        })
        _save_json_list(ANTI_REPEAT_LEDGER_PATH, ledger)
        print(f"  [Unique Topic Engine] Selected Unused Fresh Blueprint: {chosen_off['topic']}")
        return chosen_off

    @staticmethod
    def _invent_fresh_blueprint_via_llm(
        seed_obj: Dict[str, str],
        past_topics: List[str],
        dna: Dict[str, Any]
    ) -> Dict[str, Any]:
        seed_id = seed_obj["id"]
        vector_id = seed_obj["vector"]
        pillar = seed_obj["pillar"]
        seed_hint = seed_obj["seed_hint"]
        visual_mode = seed_obj.get("visual_mode", "human_neural_3d")

        dynamic_params = dna.get("dynamic_discovered_parameters", [])
        param_rules = "\n".join(
            [f"- {p.get('name')}: {p.get('rule')}" for p in dynamic_params[:5] if isinstance(p, dict)]
        )

        if visual_mode == "human_neural_3d":
            visual_instruction = (
                "Inside 'visuals', provide 6 strings (30-45 words each) for Vertical 9:16 3D cinema. "
                "Because this is HUMAN DARK PSYCHOLOGY, describe translucent 3D human silhouettes, glowing neural brain pathways, "
                "macro human eyes with dilating pupils, golden puppet strings, emotional aura shields, and dramatic body language in a dark obsidian studio."
            )
        else:
            visual_instruction = (
                "Inside 'visuals', provide 6 strings (30-45 words each) for Vertical 9:16 3D cinema. "
                "Describe concrete 3D physical objects, hands, smartphones, cutaway microchips, and banking vaults in a dark obsidian studio."
            )

        sys_prompt = f"""You are an Elite Indian Dark Psychology & Investigative Showrunner (Dhruv Rathee Shorts / Robert Greene / Behavioral Forensics style).
Create 1 BRAND-NEW, 100% UNIQUE viral YouTube Short blueprint based on this specific psychological/forensic seed:
PILLAR: "{pillar}"
SEED ANGLE: "{seed_hint}"

STRICT RULES:
1. NEVER repeat any topic in `past_topics_do_not_repeat`.
2. Return a FLAT JSON object with exact top-level keys: "topic", "domain", "pillar", "angle", "visuals".
3. Inside "angle", provide these exact 6 keys in natural spoken Devanagari Hindi:
   - "trigger": 7 to 9 words describing a relatable real-life human moment or action (no 'क्या आप जानते हैं')
   - "focus": 2-word punchy psychological effect or trap name in Devanagari
   - "mechanism": 18 to 21 words in Devanagari with 1 comma (',') explaining the exact brain/psychological mechanism
   - "metric": 18 to 21 words in Devanagari with 1 comma (',') citing a concrete behavioral psychology percentage, second-count, or neuro-effect
   - "twist": 18 to 21 words in Devanagari starting with 'असली खेल यह है—' revealing the deeper subconscious manipulation
   - "seekh": 17 to 20 words in Devanagari with 1 comma (',') giving a sharp counter-move or mental defense rule
   - "cliffhanger": 17 to 20 words in Devanagari asking a mind-bending question on another dark psychology trick, ending with 'अभी पार्ट टू कमेंट करें!'
4. {visual_instruction}
{param_rules}"""

        user_prompt = json.dumps({
            "pillar": pillar,
            "seed_to_write": seed_hint,
            "collision_vector_id": vector_id,
            "past_topics_do_not_repeat": past_topics[-30:]
        }, ensure_ascii=False)

        res = call_smart_llm_json(sys_prompt, user_prompt, temperature=0.65, cloud_only=True)
        if not isinstance(res, dict):
            return {}

        angle = res.get("angle")
        visuals = res.get("visuals") or res.get("visual_prompts") or []
        topic = str(res.get("topic") or "").strip()

        if isinstance(angle, dict) and topic and all(k in angle for k in ["trigger", "focus", "mechanism", "metric", "twist", "seekh", "cliffhanger"]):
            if not isinstance(visuals, list) or len(visuals) < 6:
                visuals = list(visuals) if isinstance(visuals, list) else []
                while len(visuals) < 6:
                    visuals.append(
                        "Slow macro push-in 3D cutaway of a translucent human brain glowing with crimson and cyan neural pathways in a dark obsidian studio, vertical 9:16"
                    )
            return {
                "combo_key": f"cloud_{seed_id}_{int(datetime.now().timestamp())}",
                "collision_vector_id": vector_id,
                "domain": str(res.get("domain") or pillar.split("|")[-1].strip()),
                "pillar": pillar,
                "topic": topic,
                "angle": angle,
                "visuals": visuals[:6]
            }
        return {}


def _synthesize_dynamic_hook(bp: Dict[str, Any], dna: Dict[str, Any]) -> Tuple[str, str]:
    trigger = bp["angle"]["trigger"].strip()
    focus = bp["angle"]["focus"].strip()

    hook_templates = dna.get("script_engine", {}).get("hook_templates", [])
    candidates: List[Tuple[str, str]] = []

    for ht in hook_templates:
        tpl = ht.get("template", "")
        if "{trigger}" in tpl and "{focus}" in tpl:
            rendered = tpl.replace("{trigger}", trigger).replace("{focus}", focus)
            if len(rendered.split()) <= 19:
                candidates.append((ht.get("id", "learned_hook"), rendered))

    if not candidates:
        candidates = [
            ("mind_trap_trigger", f"जब {trigger}, तभी सामने वाला '{focus}' का मनोवैज्ञानिक जाल बिछाता है!"),
            ("subconscious_betrayal", f"सावधान! जैसे ही {trigger}, आपके दिमाग में '{focus}' एक्टिव हो जाता है!"),
            ("power_reversal_hook", f"अगर {trigger}, तो समझ जाइए '{focus}' का खामोश खेल शुरू हो चुका है!")
        ]

    valid = [(hid, htxt) for hid, htxt in candidates if len(htxt.split()) <= 19]
    if valid:
        hook_id, chosen_txt = random.choice(valid)
    else:
        hook_id = "mind_trap_trigger"
        chosen_txt = f"सावधान! जब {trigger}, तभी '{focus}' का खेल शुरू होता है!"

    return hook_id, _clean_and_normalize_hinglish(chosen_txt)


def _build_cohesive_6_scenes(bp: Dict[str, Any], dna: Dict[str, Any]) -> List[Dict[str, Any]]:
    angle = bp["angle"]
    visuals = bp["visuals"]

    hook_id, scene_1_hook = _synthesize_dynamic_hook(bp, dna)
    bp["hook_archetype_id"] = hook_id
    bp["twist_archetype_id"] = "escalation_reveal"

    seekh_raw = angle["seekh"].strip()
    if not seekh_raw.startswith("बचने"):
        seekh_line = f"बचने का सीधा नियम—{seekh_raw}।"
    else:
        seekh_line = seekh_raw

    raw_narrations = [
        scene_1_hook,
        _clean_and_normalize_hinglish(angle["mechanism"]),
        _clean_and_normalize_hinglish(angle["metric"]),
        _clean_and_normalize_hinglish(angle["twist"]),
        _clean_and_normalize_hinglish(seekh_line),
        _clean_and_normalize_hinglish(angle["cliffhanger"]),
    ]

    scenes: List[Dict[str, Any]] = []
    for idx in range(len(raw_narrations)):
        narration = raw_narrations[idx]
        scenes.append({
            "scene_number": idx + 1,
            "narration_hinglish": narration,
            "word_count": len(narration.split()),
            "visual_prompt": visuals[idx % len(visuals)]
        })
    return scenes


def generate_viral_script() -> Dict[str, Any]:
    history = _load_json_list(HISTORY_PATH)
    dna = load_trend_dna()

    bp = CohesiveTopicEngine.select_cohesive_blueprint(history, dna)
    video_id = f"EXP_{datetime.now().strftime('%Y%m%d')}_{len(history) + 1:03d}"

    draft_scenes = _build_cohesive_6_scenes(bp, dna)
    print(f"  [Script Pre-Check] Hook='{bp.get('hook_archetype_id')}' ({draft_scenes[0]['word_count']}w) | Draft Words={sum(s['word_count'] for s in draft_scenes)}")

    final_scenes, honest_audit = run_honest_critic_and_auto_fix(draft_scenes, bp["topic"], dna)

    if final_scenes[0]["word_count"] > 19:
        _, clean_hook = _synthesize_dynamic_hook(bp, dna)
        final_scenes[0]["narration_hinglish"] = clean_hook
        final_scenes[0]["word_count"] = len(clean_hook.split())

    total_words = sum(s["word_count"] for s in final_scenes)
    est_sec = round(total_words / 2.60, 1)

    active_audio = dna.get("audio_engine", {}).get("active_cadence_profile", "high_tension_documentary")
    active_visual = dna.get("video_engine", {}).get("active_visual_style", "forensic_3d_cutaway")
    active_edit = dna.get("assembly_engine", {}).get("active_edit_profile", "viral_center_yellow")

    print("\n=======================================================")
    print(f"Video ID       : {video_id}")
    print(f"Trend DNA Ver  : {dna.get('version', 'v2.5-self-evolving')}")
    print(f"Hook Template  : {bp.get('hook_archetype_id')} ({final_scenes[0]['word_count']} words)")
    print(f"Honest Critic  : {honest_audit.get('initial_honest_score_100')} -> {honest_audit.get('final_post_fix_score_100')}/100")
    print(f"Pillar         : {bp['pillar']}")
    print(f"Topic          : {bp['topic']}")
    print(f"Pacing Lock    : {total_words} words (~{est_sec}s target 46-54s)")
    print("=======================================================")
    for sc in final_scenes:
        print(f"  [Scene {sc['scene_number']} | {sc['word_count']}w]: {sc['narration_hinglish']}")
    print("=======================================================")

    payload = {
        "video_id": video_id,
        "timestamp": datetime.now().isoformat(),
        "combo_key": bp["combo_key"],
        "seed_id": bp.get("seed_id", ""),
        "collision_vector_id": bp["collision_vector_id"],
        "domain": bp["domain"],
        "hook_archetype_id": bp.get("hook_archetype_id", "mind_trap_trigger"),
        "twist_archetype_id": bp.get("twist_archetype_id", "escalation_reveal"),
        "audio_profile_id": active_audio,
        "visual_style_id": active_visual,
        "edit_profile_id": active_edit,
        "trend_dna_version": dna.get("version", "v2.5-self-evolving"),
        "pillar": bp["pillar"],
        "topic": bp["topic"],
        "total_words": total_words,
        "estimated_duration_sec": est_sec,
        "honest_audit": honest_audit,
        "scenes": final_scenes
    }

    history.append(payload)
    _save_json_list(HISTORY_PATH, history)
    return payload


if __name__ == "__main__":
    generate_viral_script()