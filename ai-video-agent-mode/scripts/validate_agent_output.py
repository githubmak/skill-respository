"""Validate director/prompt agent output."""
import json, os, sys
from validator.field_types import validate_field_types
from validator.quality import quality_check_director, quality_check_prompt


def validate(packet_path, role="director", min_chars=500):
    """Run full validation pipeline.

    Args:
        packet_path: Path to agent output JSON
        role: "director" or "prompt"
        min_chars: Minimum chars for full_prompt (prompt role only)

    Returns:
        dict with keys:
          valid (bool) - overall pass/fail
          issues (list) - all issues found
          retry_needed (bool) - True if any blocking issue requires retry
    """
    if not os.path.exists(packet_path):
        return {"valid": False, "issues": [("FILE", "not_found", 0, "")], "retry_needed": True}

    # Step 1: Field type validation
    field_issues = validate_field_types(packet_path)

    # Step 2: Content quality checks
    if role == "director":
        quality_issues = quality_check_director(packet_path)
    else:
        quality_issues = quality_check_prompt(packet_path, minc=min_chars)

    all_issues = field_issues + quality_issues

    # Step 3: Determine if retry is needed
    retry_needed = len(all_issues) > 0
    valid = not retry_needed

    if all_issues:
        print("[VALIDATE] %s - %d issue(s) found" % (role, len(all_issues)))
        for iss in all_issues[:5]:
            print("  [%s] %s: %s vs expected %s" % (iss[1], iss[0], iss[2], iss[3]))
        if len(all_issues) > 5:
            print("  ... and %d more" % (len(all_issues) - 5))
    else:
        print("[VALIDATE] %s - PASS" % role)

    return {"valid": valid, "issues": all_issues, "retry_needed": retry_needed}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: validate_agent_output.py <packet_path> [role]")
        sys.exit(1)
    role = sys.argv[2] if len(sys.argv) > 2 else "director"
    result = validate(sys.argv[1], role)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["valid"] else 1)
