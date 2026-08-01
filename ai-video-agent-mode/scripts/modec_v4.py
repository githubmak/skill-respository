"""Deprecated import bridge for the former generational module name.

Current code must import prompt_contract.  This bridge exists only for callers
that have not yet migrated and contains no independent contract definitions.
"""

from prompt_contract import *  # noqa: F401,F403
