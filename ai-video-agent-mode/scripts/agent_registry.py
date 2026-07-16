
"""Agent ID registry - tracks spawned agents for send_input reuse."""
import json, os


def get_registry_path(run_dir):
    """Get path to agent registry file."""
    return os.path.join(run_dir, ".cache", "agents.json")


def register(run_dir, role, agent_id, status="active"):
    """Register or update an agent in the registry.
    
    Args:
        run_dir: Run directory path
        role: "emotion_analysis", "scene_analysis", "camera_movement", "qa_integration"
        agent_id: The spawn_agent returned agent_id
        status: "active", "completed", "failed"
    """
    path = get_registry_path(run_dir)
    registry = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            try:
                registry = json.load(f)
            except json.JSONDecodeError:
                registry = {}
    
    registry[role] = {
        "agent_id": agent_id,
        "status": status
    }
    
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)
    
    print("[AGENT_REG] %s = %s (%s)" % (role, agent_id, status))


def get_agent_id(run_dir, role):
    """Get agent ID for a role. Returns None if not registered."""
    path = get_registry_path(run_dir)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        try:
            registry = json.load(f)
        except json.JSONDecodeError:
            return None
    entry = registry.get(role)
    return entry["agent_id"] if entry else None


def set_status(run_dir, role, status):
    """Update status of an agent."""
    path = get_registry_path(run_dir)
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        registry = json.load(f)
    if role in registry:
        registry[role]["status"] = status
    with open(path, "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)


def list_active(run_dir):
    """List all active agents."""
    path = get_registry_path(run_dir)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
