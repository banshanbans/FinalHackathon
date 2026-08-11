"""Optional AgentSociety2 adapter boundary.

The MVP deliberately ships the Asyncio adapter as the reliable baseline. The
AgentSociety2 dependency is optional and this module records the SPIKE-001
decision without leaking framework types into public contracts.
"""

from importlib.util import find_spec


def agentsociety_available() -> bool:
    return find_spec("agentsociety2") is not None


SPIKE_STATUS = "CONDITIONAL_GO_OPTIONAL_ONLY"
SPIKE_REPORT = "docs/adr/001-agentsociety2-runtime-spike.md"
