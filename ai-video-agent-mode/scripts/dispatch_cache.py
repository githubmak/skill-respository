"""Write compact on-disk dispatch packets for sub-agent phases.

The main agent can pass these packet paths to workers instead of copying a
large shot list into every prompt. Workers read the packet from disk, write only
their required output file, and retry messages carry only failed subshot ids.
"""
import json
import os
import sys

if not os.environ.get("PYTHONPYCACHEPREFIX") and not getattr(sys, "pycache_prefix", None):
    sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(__file__))
from pycache_policy import block_source_pycache_until_run_dir, ensure_pycache_prefix

block_source_pycache_until_run_dir()


PHASE_OUTPUTS = {
    "emotion_analysis": ".cache/analysis/emotion_output.json",
    "scene_analysis": ".cache/analysis/scene_output.json",
    "camera_movement": ".cache/analysis/camera_output.json",
    "prompt_composer": ".cache/prompt_package.json",
}

PHASE_INPUTS = {
    "emotion_analysis": ".cache/orchestrator/shot_plan.json",
    "scene_analysis": ".cache/orchestrator/shot_plan.json",
    "camera_movement": ".cache/orchestrator/shot_plan.json",
    "prompt_composer": ".cache/director/director_pass.json",
}


def prepare_dispatch_packet(run_dir, phase, batch_size=None, subshot_ids=None):
    """Materialize a phase input packet and return its path.

    The packet intentionally stores file paths plus compact subshot metadata.
    A worker should read source files from the paths in the packet instead of
    receiving full source text in the spawn message.
    """
    ensure_pycache_prefix(run_dir)
    source_path = os.path.join(run_dir, PHASE_INPUTS.get(phase, ""))
    if not source_path or not os.path.exists(source_path):
        return None

    data = _load_json(source_path)
    wanted = set(subshot_ids or [])
    items = _extract_items(data, wanted)
    packet = {
        "phase": phase,
        "run_dir": run_dir,
        "source_path": source_path,
        "project_config_path": os.path.join(run_dir, "project_config.json"),
        "output_path": os.path.join(run_dir, PHASE_OUTPUTS.get(phase, ".cache/%s_output.json" % phase)),
        "batch_size": batch_size,
        "subshot_count": len(items),
        "items": items,
        "instruction": "Read source_path and process only items listed here. Do not paste unchanged source content back into chat; write the output_path JSON file.",
    }

    out_dir = os.path.join(run_dir, ".cache", "dispatch")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "%s_packet.json" % phase)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(packet, f, ensure_ascii=False, indent=2)
    return out_path


def prepare_parallel_dispatch(run_dir, phases, batch_sizes=None):
    batch_sizes = batch_sizes or {}
    return {
        phase: prepare_dispatch_packet(run_dir, phase, batch_sizes.get(phase))
        for phase in phases
    }


def _extract_items(data, wanted):
    if "shots" in data:
        items = []
        for shot in data.get("shots", []):
            for ss in shot.get("subshots", []):
                ssid = ss.get("subshot_id", "")
                if wanted and ssid not in wanted:
                    continue
                items.append({
                    "shot_id": shot.get("shot_id", ""),
                    "subshot_id": ssid,
                    "scene": shot.get("scene", ""),
                    "duration": ss.get("duration", 0),
                    "shot_size": ss.get("shot_size", ""),
                    "base_action": ss.get("base_action", ""),
                    "shot_type": ss.get("shot_type", "") or ss.get("visual_type", "") or ss.get("purpose", ""),
                    "visual_intent": ss.get("visual_intent", "") or ss.get("image_subject", "") or ss.get("atmosphere", ""),
                    "characters": ss.get("characters", []),
                    "dialogue_refs": ss.get("dialogue_refs", []),
                    "emotion_tone": ss.get("emotion_tone", ""),
                })
        return items
    return [
        {
            "shot_id": item.get("shot_id", ""),
            "subshot_id": item.get("subshot_id", ""),
            "duration": item.get("duration", 0),
            "shot_size": item.get("shot_size", ""),
        }
        for item in data.get("items", [])
        if not wanted or item.get("subshot_id") in wanted
    ]


def _load_json(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)
