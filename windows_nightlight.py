"""Read-only detection for Windows' built-in Night Light state.

Windows does not expose a public desktop API for the inbox Night Light switch.
Its current state is stored in the per-user CloudStore payload below. This
module only reads the payload; it never changes the Windows setting.

The payload is a marshaled Microsoft Bond CompactBinary v1 struct (CloudStore
wrapper) whose field 1.1.1 is a ``list<int8>`` carrying a second marshaled
struct. Inside that inner struct the *presence* of field 0 (an int32 that is
always 0) means Night Light is force-enabled; its absence means it is off.
Byte 18 of the blob is therefore only the inner payload length, not a state
marker, and it varies between Windows builds (0x13/0x15 on builds that also
write an "initialized" field 10, 0x10/0x12 on Windows 11 build 26200 which
omits it). Anything the structural parser cannot account for is reported as
unknown so the HT filter fails safe (paused).
"""

from dataclasses import dataclass
from typing import Optional
import winreg


STATE_KEY = (
    r"Software\Microsoft\Windows\CurrentVersion\CloudStore\Store\DefaultAccount\Current"
    r"\default$windows.data.bluelightreduction.bluelightreductionstate"
    r"\windows.data.bluelightreduction.bluelightreductionstate"
)
STATE_VALUE = "Data"
_HEADER = b"CB\x01\x00"

# Bond CompactBinary type ids.
_BT_STOP, _BT_STOP_BASE, _BT_BOOL = 0, 1, 2
_BT_UINT8, _BT_UINT16, _BT_UINT32, _BT_UINT64 = 3, 4, 5, 6
_BT_FLOAT, _BT_DOUBLE, _BT_STRING, _BT_STRUCT = 7, 8, 9, 10
_BT_LIST, _BT_SET, _BT_MAP = 11, 12, 13
_BT_INT8, _BT_INT16, _BT_INT32, _BT_INT64, _BT_WSTRING = 14, 15, 16, 17, 18
_VARINT_TYPES = frozenset((_BT_UINT16, _BT_UINT32, _BT_UINT64, _BT_INT16, _BT_INT32, _BT_INT64))
_MAX_ITEMS = 4096

_INNER_ENABLED_FIELD = 0      # int32, presence == force-enabled
_OUTER_PAYLOAD_FIELD = 1      # struct -> struct -> list<int8>


class _Malformed(ValueError):
    """The blob does not match the known Bond/CloudStore structure."""


class _Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def byte(self) -> int:
        if self.pos >= len(self.data):
            raise _Malformed("truncated")
        value = self.data[self.pos]
        self.pos += 1
        return value

    def take(self, count: int) -> bytes:
        if count < 0 or self.pos + count > len(self.data):
            raise _Malformed("truncated")
        chunk = self.data[self.pos:self.pos + count]
        self.pos += count
        return chunk

    def varint(self) -> int:
        result, shift = 0, 0
        for _ in range(10):
            value = self.byte()
            result |= (value & 0x7F) << shift
            if not value & 0x80:
                return result
            shift += 7
        raise _Malformed("varint too long")

    def header(self) -> None:
        """Marshaled CompactBinary v1 header; unknown versions are rejected."""
        if self.take(4) != _HEADER:
            raise _Malformed("header")

    def field(self):
        """Return (type, id); STOP/STOP_BASE carry no id."""
        raw = self.byte()
        bond_type, packed = raw & 0x1F, raw >> 5
        if bond_type in (_BT_STOP, _BT_STOP_BASE):
            return bond_type, 0
        if packed <= 5:
            return bond_type, packed
        if packed == 6:
            return bond_type, self.byte()
        return bond_type, self.byte() | (self.byte() << 8)

    def container(self):
        """v1 container header: element type byte then count varint."""
        element = self.byte() & 0x1F
        count = self.varint()
        if count > _MAX_ITEMS:
            raise _Malformed("container too large")
        return element, count

    def skip(self, bond_type: int, depth: int = 0) -> None:
        if depth > 16:
            raise _Malformed("nesting")
        if bond_type in (_BT_BOOL, _BT_UINT8, _BT_INT8):
            self.byte()
        elif bond_type in _VARINT_TYPES:
            self.varint()
        elif bond_type == _BT_FLOAT:
            self.take(4)
        elif bond_type == _BT_DOUBLE:
            self.take(8)
        elif bond_type == _BT_STRING:
            self.take(self.varint())
        elif bond_type == _BT_WSTRING:
            self.take(2 * self.varint())
        elif bond_type == _BT_STRUCT:
            self.skip_struct(depth + 1)
        elif bond_type in (_BT_LIST, _BT_SET):
            element, count = self.container()
            for _ in range(count):
                self.skip(element, depth + 1)
        elif bond_type == _BT_MAP:
            key_type = self.byte() & 0x1F
            value_type = self.byte() & 0x1F
            count = self.varint()
            if count > _MAX_ITEMS:
                raise _Malformed("map too large")
            for _ in range(count):
                self.skip(key_type, depth + 1)
                self.skip(value_type, depth + 1)
        else:
            raise _Malformed(f"unsupported type {bond_type}")

    def skip_struct(self, depth: int = 0) -> None:
        while True:
            bond_type, _ = self.field()
            if bond_type == _BT_STOP:
                return
            if bond_type == _BT_STOP_BASE:
                continue
            self.skip(bond_type, depth)


def _walk_struct(reader: _Reader):
    """Yield (type, id) for each field of the current struct until STOP."""
    while True:
        bond_type, field_id = reader.field()
        if bond_type == _BT_STOP:
            return
        if bond_type == _BT_STOP_BASE:
            continue
        yield bond_type, field_id


def _inner_payload(reader: _Reader) -> bytes:
    """Walk the CloudStore wrapper and return the inner marshaled struct bytes."""
    reader.header()
    payload = None
    for bond_type, field_id in _walk_struct(reader):
        if not (field_id == _OUTER_PAYLOAD_FIELD and bond_type == _BT_STRUCT):
            reader.skip(bond_type)
            continue
        for bond_type, field_id in _walk_struct(reader):
            if not (field_id == 1 and bond_type == _BT_STRUCT):
                reader.skip(bond_type)
                continue
            for bond_type, field_id in _walk_struct(reader):
                if not (field_id == 1 and bond_type == _BT_LIST):
                    reader.skip(bond_type)
                    continue
                element, count = reader.container()
                if element != _BT_INT8:
                    raise _Malformed("payload element type")
                if payload is not None:
                    raise _Malformed("duplicate payload")
                payload = reader.take(count)
    if payload is None:
        raise _Malformed("missing payload")
    return payload


@dataclass(frozen=True)
class WindowsNightLightStatus:
    is_enabled: Optional[bool]
    detail: str

    @property
    def is_available(self) -> bool:
        return self.is_enabled is not None


def parse_cloudstore_state(data: bytes) -> WindowsNightLightStatus:
    """Decode the CloudStore record structurally; never guess from one byte."""
    if not isinstance(data, bytes) or data[:4] != _HEADER:
        return WindowsNightLightStatus(None, "Windows Night Light state format is unsupported")
    try:
        inner = _Reader(_inner_payload(_Reader(data)))
        inner.header()
        enabled = False
        for bond_type, field_id in _walk_struct(inner):
            if field_id == _INNER_ENABLED_FIELD:
                if bond_type != _BT_INT32:
                    raise _Malformed("enabled field type")
                inner.varint()
                enabled = True
            else:
                inner.skip(bond_type)
        if inner.pos != len(inner.data):
            raise _Malformed("trailing inner bytes")
    except _Malformed:
        return WindowsNightLightStatus(None, "Windows Night Light state is unknown")
    if enabled:
        return WindowsNightLightStatus(True, "Windows Night Light is on")
    return WindowsNightLightStatus(False, "Windows Night Light is off")


def get_windows_nightlight_status() -> WindowsNightLightStatus:
    """Returns the current native Night Light state, or unknown safely."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STATE_KEY) as key:
            data, value_type = winreg.QueryValueEx(key, STATE_VALUE)
    except FileNotFoundError:
        return WindowsNightLightStatus(None, "Windows Night Light state is unavailable")
    except OSError as exc:
        return WindowsNightLightStatus(None, f"Could not read Windows Night Light ({exc})")

    if value_type != winreg.REG_BINARY or not isinstance(data, bytes):
        return WindowsNightLightStatus(None, "Windows Night Light returned an unsupported state")
    return parse_cloudstore_state(data)
