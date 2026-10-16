"""Decoder for the frame stream found in Bosch UDF binary payloads.

Each frame is ``00 FF`` + u64 timestamp (ns since power-on) followed by
``[u16 field id][payload]`` items. Payload sizes come from the UDF schema, and
different frames may carry different field subsets.
"""

import struct
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from bme_udf_container import UDFContainer

FRAME_MARKER = b"\x00\xff"
FRAME_HEADER_SIZE = 10

_SCALAR_FORMATS = {
    "f": "<f",
    "u8": "<B",
    "s8": "<b",
    "u16": "<H",
    "s16": "<h",
    "u32": "<I",
    "s32": "<i",
    "u64": "<Q",
    "s64": "<q",
}


@dataclass
class UDFFrame:
    """One timestamped frame with raw field payloads keyed by field id."""

    timestamp_ns: int
    fields: Dict[int, bytes] = field(default_factory=dict)

    @property
    def timestamp_ms(self) -> int:
        return self.timestamp_ns // 1_000_000


@dataclass
class UDFFrameStream:
    frames: List[UDFFrame]
    schema: Dict[int, Dict[str, Any]]
    truncated: bool = False
    error: Optional[str] = None


def decode_value(payload: bytes, type_spec: str) -> Tuple[Any, ...]:
    """Decode a payload using a schema type such as ``f``, ``u32`` or ``f,u8``."""
    values = []
    offset = 0
    for part in (p.strip() for p in type_spec.split(",")):
        fmt = _SCALAR_FORMATS.get(part)
        if fmt is None:
            raise ValueError(f"Unsupported UDF field type: {part!r}")
        size = struct.calcsize(fmt)
        values.append(struct.unpack_from(fmt, payload, offset)[0])
        offset += size
    return tuple(values)


class UDFFrameDecoder:
    """Split a UDF payload into frames, tolerating a truncated tail."""

    def decode(self, container: UDFContainer) -> UDFFrameStream:
        schema = {f["id"]: f for f in container.fields}
        data = container.binary_data
        frames: List[UDFFrame] = []
        position = 0
        length = len(data)
        error = None

        while position < length:
            if data[position : position + 2] != FRAME_MARKER:
                error = f"Expected frame marker at offset {position}"
                break
            if position + FRAME_HEADER_SIZE > length:
                error = f"Truncated frame header at offset {position}"
                break

            frame = UDFFrame(
                timestamp_ns=int.from_bytes(
                    data[position + 2 : position + FRAME_HEADER_SIZE], "little"
                )
            )
            cursor = position + FRAME_HEADER_SIZE
            frame_ok = True
            while cursor < length and data[cursor : cursor + 2] != FRAME_MARKER:
                if cursor + 2 > length:
                    frame_ok = False
                    error = f"Truncated field id at offset {cursor}"
                    break
                field_id = int.from_bytes(data[cursor : cursor + 2], "little")
                definition = schema.get(field_id)
                if definition is None:
                    frame_ok = False
                    error = f"Unknown field id {field_id} at offset {cursor}"
                    break
                size = definition["size"]
                if cursor + 2 + size > length:
                    frame_ok = False
                    error = f"Truncated field {field_id} at offset {cursor}"
                    break
                frame.fields[field_id] = data[cursor + 2 : cursor + 2 + size]
                cursor += 2 + size

            if not frame_ok:
                break
            frames.append(frame)
            position = cursor

        return UDFFrameStream(
            frames=frames, schema=schema, truncated=error is not None, error=error
        )


def _version_string(payload: bytes, parts: int) -> str:
    return ".".join(str(byte) for byte in payload[:parts])


def read_device_info(stream: UDFFrameStream) -> Dict[str, Any]:
    """Extract BSEC version (50), firmware version (51) and board type (52).

    Versions are packed one byte per component; BSEC uses four components and
    firmware three. Missing values are omitted.
    """
    info: Dict[str, Any] = {}
    for frame in stream.frames:
        if 50 in frame.fields:
            info["bsec_version"] = _version_string(frame.fields[50], 4)
        if 51 in frame.fields:
            info["firmware_version"] = _version_string(frame.fields[51], 3)
        if 52 in frame.fields:
            info["board_type"] = str(
                int.from_bytes(frame.fields[52], "little", signed=True)
            )
        if len(info) == 3:
            break
    return info
