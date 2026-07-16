"""Pipeline orchestration engine - state-driven, tick-based."""
import json, os, sys

sys.path.insert(0, os.path.dirname(__file__))
from pipeline_templates import GATES
from pipeline_state import (
    load_state, save_state, set_agent_id,
    mark_waiting, mark_done, mark_failed, advance, init_state
)
from sources import init_sources, set_batch_agent, get_failed_subshots, mark_subshot_failed
from gate_check import check as gate_check
from assemble_director import run as assemble_director


def run(run_dir):
    """One pipeline tick. Returns action dict for main agent."""
    state = load_state(run_dir)
    phase = state['current_phase']
    phase_info = state['phases'].get(phase, {})
    status = phase_info.get('status', 'pending')
    phase_config = GATES.get(phase)

    if not phase_config:
        return {'action': 'completed'}

    if status == 'done':
        advance(run_dir)
        new_phase = load_state(run_dir)['current_phase']
        return {'action': 'advance', 'next': new_phase, 'from': phase}

    if status == 'failed' and phase_info.get('retries', 0) > 0:
        retries = phase_info.get('retries', 0)
        agent_id = phase_info.get('agent_id')
        if retries >= 2:
            return {'action': 'blocked', 'phase': phase, 'reason': 'max_retries(2)'}
        failed = get_failed_subshots(run_dir, _phase_to_role(phase))
        return {'action': 'send_back', 'phase': phase, 'agent_id': agent_id, 'shots': failed}

    missing = _missing_inputs(run_dir, phase_config)
    if missing:
        return {'action': 'blocked', 'phase': phase, 'reason': 'missing: %s' % missing}

    agent_id = phase_info.get('agent_id')
    if not agent_id:
        return {'action': 'spawn', 'phase': phase, 'role': _phase_to_role(phase)}

    if not _outputs_exist(run_dir, phase_config):
        mark_waiting(run_dir, phase)
        return {'action': 'waiting', 'phase': phase}

    issues = _validate(run_dir, phase, phase_config)
    if issues:
        for iss in issues:
            subshot_id = iss.get("msg", "").split("]")[0] if "]" in iss.get("msg","") else "GLOBAL"
            mark_subshot_failed(run_dir, subshot_id, (iss.get("check","?"), iss.get("msg","")))
        mark_failed(run_dir, phase)
        return {'action': 'failed', 'phase': phase, 'issues': issues[:10]}

    mark_done(run_dir, phase)
    advance(run_dir)
    new_phase = load_state(run_dir)['current_phase']
    return {'action': 'advance', 'next': new_phase, 'from': phase}



def _assemble_analysis(run_dir):
    paths = {
        'emotion': os.path.join(run_dir, '.cache', 'analysis', 'emotion_output.json'),
        'scene': os.path.join(run_dir, '.cache', 'analysis', 'scene_output.json'),
        'camera': os.path.join(run_dir, '.cache', 'analysis', 'camera_output.json'),
        'plan': os.path.join(run_dir, '.cache', 'orchestrator', 'shot_plan.json'),
    }
    out = os.path.join(run_dir, '.cache', 'director', 'director_pass.json')
    ep = paths['emotion'] if os.path.exists(paths['emotion']) else None
    sp = paths['scene'] if os.path.exists(paths['scene']) else None
    cp = paths['camera'] if os.path.exists(paths['camera']) else None
    if os.path.exists(paths['plan']):
        assemble_director(ep, sp, cp, paths['plan'], out)


def _phase_to_role(phase):

    m = {
        'emotion_analysis': 'emotion_analysis',
        'scene_analysis': 'scene_analysis',
        'camera_movement': 'camera_movement',
        'qa_integration': 'qa_integration',
        'prompt_composer': 'prompt',
    }
    return m.get(phase, phase)


def _missing_inputs(run_dir, config):
    missing = []
    for inp in config.get('input', []):
        if not os.path.exists(os.path.join(run_dir, inp)):
            missing.append(inp)
    return missing


def _outputs_exist(run_dir, config):
    for out in config.get('output', []):
        if not os.path.exists(os.path.join(run_dir, '.cache', out)):
            return False
    return True


def _validate(run_dir, phase, config):
    """Run gate check for output validation. Returns list of issue dicts, or empty if pass."""
    gc = gate_check(run_dir, phase, strict=False)
    if gc["bypass_detected"]:
        return [{"check": "BYPASS", "severity": "blocking", "msg": "Output existed before spawn"}]
    return [i for i in gc["issues"] if i["severity"] == "blocking"]