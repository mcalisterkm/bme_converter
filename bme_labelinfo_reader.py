"""Read Bosch label information in JSON or raw ``.labelinfo`` text form."""

import json
import random
import string
import time
from pathlib import Path
from typing import Any, Dict

_BASE36 = string.digits + string.ascii_lowercase


def read_labelinfo(path: str) -> Dict[str, Any]:
    """Return a ``labelInfoHeader``/``labelInformation`` document.

    ``.bmelabelinfo`` is JSON. The raw ``.labelinfo`` written by AI Studio is
    ``Key:Value`` header lines followed by label objects, one per line.
    """
    text = Path(path).read_text(encoding="utf-8-sig")
    try:
        document = json.loads(text)
    except json.JSONDecodeError:
        return _parse_raw_labelinfo(text)
    if not isinstance(document, dict):
        raise ValueError(f"Unexpected label information in {path}")
    return document


def _parse_raw_labelinfo(text: str) -> Dict[str, Any]:
    header: Dict[str, Any] = {}
    labels = []
    for line in text.splitlines():
        line = line.strip().lstrip(",").rstrip(",").strip()
        if not line:
            continue
        if line.startswith("{"):
            labels.append(json.loads(line))
            continue
        key, separator, value = line.partition(":")
        if not separator:
            raise ValueError(f"Unrecognised label information line: {line!r}")
        key = key.strip()
        if key == "FirmwareVersion":
            header["firmwareVersion"] = value.strip()
        elif key == "BoardType":
            header["boardId"] = value.strip()
    return {"labelInfoHeader": header, "labelInformation": labels}


def generate_seed() -> str:
    """Create a 16-character base-36 power-on seed (time prefix + random)."""
    prefix = ""
    stamp = int(time.time())
    while stamp:
        stamp, digit = divmod(stamp, 36)
        prefix = _BASE36[digit] + prefix
    suffix = "".join(random.choices(_BASE36, k=16 - len(prefix)))
    return (prefix + suffix)[:16]
