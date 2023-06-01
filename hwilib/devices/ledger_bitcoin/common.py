from io import BytesIO
from typing import List, Optional, Literal
from enum import Enum
from typing import Union

import hashlib

UINT64_MAX: int = 18446744073709551615
UINT32_MAX: int = 4294967295
UINT16_MAX: int = 65535


def read_varint(buf: BytesIO,
                prefix: Optional[bytes] = None) -> int:
    b: bytes = prefix if prefix else buf.read(1)

    if not b:
        raise ValueError(f"Can't read prefix: '{b}'!")

    n: int = {b"\xfd": 2, b"\xfe": 4, b"\xff": 8}.get(b, 1)  # default to 1

    b = buf.read(n) if n > 1 else b

    if len(b) != n:
        raise ValueError("Can't read varint!")

    return int.from_bytes(b, byteorder="little")


def read_uint(buf: BytesIO,
              bit_len: int,
              byteorder: Literal['big', 'little'] = 'little') -> int:
    size: int = bit_len // 8
    b: bytes = buf.read(size)

    if len(b) < size:
        raise ValueError(f"Can't read u{bit_len} in buffer!")

    return int.from_bytes(b, byteorder)

class ByteStreamParser:
    def __init__(self, input: bytes):
        self.stream = BytesIO(input)

    def assert_empty(self) -> bytes:
        if self.stream.read(1) != b'':
            raise ValueError("Byte stream was expected to be empty")

    def read_bytes(self, n: int) -> bytes:
        result = self.stream.read(n)
        if len(result) < n:
            raise ValueError("Byte stream exhausted")
        return result

    def read_uint(self, n: int, byteorder: Literal['big', 'little'] = "big") -> int:
        return int.from_bytes(self.read_bytes(n), byteorder)

    def read_varint(self) -> int:
        prefix = self.read_uint(1)

        if prefix == 253:
            return self.read_uint(2, 'little')
        elif prefix == 254:
            return self.read_uint(4, 'little')
        elif prefix == 255:
            return self.read_uint(8, 'little')
        else:
            return prefix
