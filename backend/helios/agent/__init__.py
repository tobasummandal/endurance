"""Pattern A — agent integration.

A coding agent (or any tool-using LLM) calls these to invoke Helios on code
it just generated. Three layers:

- HeliosClient        — typed HTTP client over the Helios backend
- review_code()       — high-level "audit + warn if non-scientific"
- TOOL_SCHEMAS        — OpenAI/Anthropic-shaped function schemas to register
"""
from .client import HeliosClient, HeliosClientError  # noqa: F401
from .review import Review, review_code  # noqa: F401
from .tool_schema import TOOL_SCHEMAS, ANTHROPIC_TOOLS, OPENAI_TOOLS  # noqa: F401
