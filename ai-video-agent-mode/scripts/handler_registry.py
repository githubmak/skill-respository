"""Plugin handler registry for pipeline phases.
Extend by importing register_handler in any script:

    from handler_registry import register_handler

    @register_handler("my_new_phase")
    def handle_my_phase(run_dir):
        ...
"""
PHASE_HANDLERS = {}


def register_handler(phase_name):
    """Decorator: register a handler function for a pipeline phase.

    The handler receives (run_dir) and should produce the phase output file(s).
    """
    def wrapper(fn):
        PHASE_HANDLERS[phase_name] = fn
        print("[HANDLER] Registered phase: %s -> %s" % (phase_name, fn.__name__))
        return fn
    return wrapper


def get_handler(phase_name):
    """Get the registered handler for a phase, or None."""
    return PHASE_HANDLERS.get(phase_name)
