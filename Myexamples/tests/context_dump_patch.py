"""Debug patch to dump raw context before ScoreBasedContextCreator truncation."""

import json
from datetime import datetime
from pathlib import Path

from camel.memories.context_creators.score_based import ScoreBasedContextCreator

_original_create_context = ScoreBasedContextCreator.create_context


def _to_serializable(value):
    if value is None:
        return None

    try:
        import uuid
        from datetime import datetime
    except Exception:  # pragma: no cover - fallback protection
        uuid = None
        datetime = None

    if uuid and isinstance(value, uuid.UUID):
        return str(value)
    if datetime and isinstance(value, datetime):
        return value.isoformat()
    return value


def _ensure_serializable(record):
    memory_record = getattr(record, "memory_record", None)
    if memory_record is None:
        return str(record)

    msg = memory_record.message
    payload = {
        "uuid": _to_serializable(getattr(memory_record, "uuid", None)),
        "role": getattr(memory_record, "role_at_backend", None),
        "timestamp": _to_serializable(getattr(memory_record, "created_at", None)),
        "score": getattr(record, "score", None),
        "record_idx": getattr(record, "idx", None),
    }

    if msg is None:
        payload["content"] = None
        return payload

    if hasattr(msg, "to_dict"):
        payload["content"] = msg.to_dict()
    elif isinstance(msg, dict):
        payload["content"] = msg
    else:
        payload["content"] = str(msg)

    return payload


def patched_create_context(self, records):
    total_tokens = 0
    try:
        total_tokens = self.token_counter.count_tokens_from_messages(
            [record.memory_record.to_openai_message() for record in records if record.memory_record]
        )
    except Exception:
        pass

    if total_tokens > self.token_limit:
        dump_dir = Path("debug_context")
        dump_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = dump_dir / f"raw_context_{total_tokens}_{self.token_limit}_{timestamp}.json"

        serializable = [_ensure_serializable(record) for record in records]
        payload = {
            "total_tokens_before": total_tokens,
            "token_limit": self.token_limit,
            "records_count": len(records),
            "records": serializable,
        }

        with file_path.open("w", encoding="utf-8") as fout:
            json.dump(payload, fout, ensure_ascii=False, indent=2, default=str)

    return _original_create_context(self, records)


ScoreBasedContextCreator.create_context = patched_create_context
