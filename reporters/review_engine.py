from typing import List, Dict, Any
from models import MasterIdentity


class ReviewEngine:
    """
    Performs logical consistency checks on identity data, surfacing things an
    analyst should double-check rather than silently trusting the fused
    identity.
    """

    LOW_CONFIDENCE_THRESHOLD = 0.5

    def check_conflicts(self, identity: MasterIdentity) -> List[str]:
        """Flags contradictory or unverified findings in the identity model.

        By the time an identity reaches here, ``identity_utils`` has already
        fused near-duplicate anchors (see ``fusion_engine.FusionEngine``), so
        any anchors of the same type that remain distinct are genuinely
        different values — worth a second look before assuming they all
        describe the same subject."""
        conflicts = []

        for label, anchors in (
            ("email", identity.email),
            ("username", identity.username),
        ):
            values = [a.value for a in anchors if a]
            if len(values) > 1:
                conflicts.append(
                    f"Multiple distinct {label} anchors found "
                    f"({', '.join(values)}) — confirm they belong to the same "
                    "subject before treating them as equivalent."
                )
            for a in anchors:
                if a and a.aggregate_confidence < self.LOW_CONFIDENCE_THRESHOLD:
                    conflicts.append(
                        f"Low-confidence {label} anchor '{a.value}' "
                        f"(confidence={a.aggregate_confidence:.2f}) — treat as unverified."
                    )

        distinct_names = sorted({n for n in identity.fullname if n})
        if len(distinct_names) > 1:
            conflicts.append(
                f"Multiple distinct full names found ({', '.join(distinct_names)}) "
                "— possible different subjects."
            )

        return conflicts

    def audit(self, identity: MasterIdentity) -> Dict[str, Any]:
        """Audits the identity and returns a status report."""
        warnings = self.check_conflicts(identity)
        return {
            "status": "PASS" if not warnings else "WARNING",
            "warnings": warnings,
            "artifact_count": len(identity.email)
            + len(identity.username)
            + len(identity.fullname),
        }
