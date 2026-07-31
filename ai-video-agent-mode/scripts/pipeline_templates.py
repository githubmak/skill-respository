"""Current-contract pipeline gate declarations."""

from contract_registry import pipeline_gates


GATES = pipeline_gates()


def get_retry_decision(result, max_retries=None):
    """Given a gate result, decide what to do. Returns 'retry', 'block', or 'pass'."""
    if result["blocked"]:
        return "block"
    if result["retry_needed"]:
        return "retry"
    return "pass"
