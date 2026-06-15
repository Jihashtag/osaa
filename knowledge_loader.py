import json
from typing import Dict, Any
from models import Knowledge


class KnowledgeLoader:
    """Utility class to load Knowledge objects from various sources."""

    @staticmethod
    def from_json(file_path: str) -> Knowledge:
        """Loads Knowledge from a JSON file."""
        with open(file_path, "r") as f:
            data = json.load(f)

        return Knowledge(
            identity=data.get("identity", {}),
            behavioral_tags=data.get("behavioral_tags", []),
            metadata=data.get("metadata", {}),
        )

    _IDENTITY_KEYS = {"email", "username", "fullname", "phone", "address"}

    @staticmethod
    def from_text(text: str, **identity_fields: Any) -> Knowledge:
        """Build Knowledge from free-text notes plus optional identity fields.

        Lets a user pass what they already know on the CLI
        (``--knowledge "..."``) without authoring a JSON file. The notes are
        carried in ``metadata['notes']`` and reach the analyst via
        ``Knowledge.to_dict()``."""
        identity = {
            k: v
            for k, v in identity_fields.items()
            if k in KnowledgeLoader._IDENTITY_KEYS and v
        }
        metadata = {"notes": text} if text else {}
        return Knowledge(identity=identity, metadata=metadata)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> Knowledge:
        """
        Loads Knowledge from a dictionary.
        Useful for converting CLI arguments into a Knowledge object.
        """
        # We assume any key provided in 'data' that belongs to identity should be mapped.
        # For simplicity, we filter known identity keys or just take the whole dict as identity if it's flat.
        identity_keys = {"email", "username", "fullname", "phone", "address"}
        identity = {
            k: v for k, v in data.items() if k in identity_keys and v is not None
        }

        return Knowledge(
            identity=identity,
            behavioral_tags=data.get("behavioral_tags", []),
            metadata=data.get("metadata", {}),
        )
