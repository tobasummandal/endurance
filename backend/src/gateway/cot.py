"""
Cursor-on-Target (CoT) message envelope. Annex D — adds tactical realism.

Wraps a routing decision as a CoT XML event with task profile fields in the
<detail> block. Real CoT consumers (ATAK, FreeTAKServer) would parse this.
For our demo we just emit the XML in the audit log so judges can see it.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from xml.sax.saxutils import escape
import uuid


def envelope(
    task_id: str,
    task_name: str,
    decision: str,
    classification_level: str,
    rationale: str,
    *,
    lat: float = 36.1447,   # Vanderbilt-ish (placeholder)
    lon: float = -86.8027,
    hae: float = 200.0,
    stale_seconds: int = 60,
) -> str:
    """Build a CoT XML event wrapping a routing decision."""
    now = datetime.now(timezone.utc)
    stale = now + timedelta(seconds=stale_seconds)
    fmt = "%Y-%m-%dT%H:%M:%S.%fZ"
    uid = f"qrb.{task_id}.{uuid.uuid4().hex[:8]}"
    cot_type = "a-f-G-U-C"  # friendly ground unit (placeholder)

    return (
        f'<event version="2.0" uid="{escape(uid)}" type="{cot_type}" '
        f'time="{now.strftime(fmt)}" start="{now.strftime(fmt)}" stale="{stale.strftime(fmt)}" how="m-g">'
        f'<point lat="{lat}" lon="{lon}" hae="{hae}" ce="9999.0" le="9999.0"/>'
        f'<detail>'
        f'<qrb_routing task_id="{escape(task_id)}" task_name="{escape(task_name)}" '
        f'decision="{escape(decision)}" classification="{escape(classification_level)}" '
        f'rationale="{escape(rationale)}"/>'
        f'</detail>'
        f'</event>'
    )
