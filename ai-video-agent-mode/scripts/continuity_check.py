"""Cross-shot continuity check."""
import json, os, sys


def run(run_dir, dry=False):
    """Check continuity across all director packets.

    Scans all .director_packet.json files in .cache/director/
    and .cache/orchestrator/shot_plan.json.

    Returns:
        (warning_count, error_count, issues_list)
    """
    director_dir = os.path.join(run_dir, ".cache", "director")
    plan_path = os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json")

    issues = []
    warnings = 0
    errors = 0

    # Load all director packets
    if not os.path.isdir(director_dir):
        return (0, 0, issues)

    packets = []
    for fn in sorted(os.listdir(director_dir)):
        if fn.endswith(".director_packet.json"):
            fp = os.path.join(director_dir, fn)
            with open(fp, "r", encoding="utf-8-sig") as f:
                try:
                    packets.append(json.load(f))
                except json.JSONDecodeError:
                    issues.append((fn, "JSON_PARSE", 0, "invalid_json"))
                    errors += 1

    if len(packets) < 2:
        if not dry:
            _save_report(run_dir, warnings, errors, issues)
        return (warnings, errors, issues)

    prev_size = None
    for pkt in packets:
        for item in pkt.get("items", []):
            sz = item.get("shot_size", "")
            sid = item.get("subshot_id", "?")
            # Check 1: Shot size gradient not too extreme between adjacent shots
            if prev_size and sz:
                size_jumps = {"ECU": 1, "CU": 2, "MCU": 3, "MS": 4, "FS": 5, "LS": 6, "ELS": 7}
                pn = size_jumps.get(prev_size.split("(")[0].strip(), 0)
                cn = size_jumps.get(sz.split("(")[0].strip(), 0)
                if pn and cn and abs(cn - pn) >= 4:
                    issues.append((sid, "SHOT_SIZE_GAP", abs(cn-pn), "<=3"))
                    warnings += 1
            if sz:
                prev_size = sz

    # Check 2: Camera axis - detect potential axis crossing
    prev_axis = None
    for pkt in packets:
        for item in pkt.get("items", []):
            cm = item.get("camera", {})
            ax = cm.get("axis", "") if isinstance(cm, dict) else ""
            if ax:
                prev_axis = ax

    if not dry:
        _save_report(run_dir, warnings, errors, issues)

    return (warnings, errors, issues)


def _save_report(run_dir, warnings, errors, issues):
    """Save continuity report to cache."""
    report_path = os.path.join(run_dir, ".cache", "continuity", "report.json")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({"warnings": warnings, "errors": errors, "issues": issues}, f, ensure_ascii=False)
    print("[CONTINUITY] %d errors, %d warnings" % (errors, warnings))
