"""Canonical speech-event kinds shared by planning and validation."""

SPEECH_KINDS = frozenset({"台词", "OS", "OV", "系统音"})
NON_LIP_SYNC_KINDS = frozenset({"OS", "OV", "系统音"})
NONPHYSICAL_SPEECH_KINDS = frozenset({"OV", "系统音"})

SYSTEM_SOUND_SPEAKERS = frozenset({"系统音", "提示音", "设备音", "广播音", "广播"})
SYSTEM_SOUND_MARKERS = ("系统音", "提示音", "设备播报", "广播音", "电子播报")


def classify_speech_kind(speaker, tone):
    speaker = str(speaker or "").strip()
    tone = str(tone or "").strip()
    tone_upper = tone.upper()
    if speaker in SYSTEM_SOUND_SPEAKERS or any(marker in tone for marker in SYSTEM_SOUND_MARKERS):
        return "系统音"
    if "OS" in tone_upper or "内心独白" in tone or "内心" in tone:
        return "OS"
    if "OV" in tone_upper or "旁白" in tone or speaker == "旁白":
        return "OV"
    return "台词"


def is_explicit_system_sound(speaker, tone=""):
    speaker = str(speaker or "").strip()
    tone = str(tone or "").strip()
    return speaker in SYSTEM_SOUND_SPEAKERS or any(marker in tone for marker in SYSTEM_SOUND_MARKERS)
