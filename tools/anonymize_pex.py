"""Replaces the user and machine names PapyrusCompiler writes into the .pex header.

Header: magic u32, version u8 u8, game id u16, compile time u64, then three strings
(u16 big-endian length + bytes): source file, user, machine. Only the last two are replaced.
"""
import pathlib
import struct
import sys

LABEL = b"CarryThem"


def read_string(data, offset):
    length = struct.unpack_from(">H", data, offset)[0]
    return data[offset + 2:offset + 2 + length], offset + 2 + length


def anonymize(path):
    data = path.read_bytes()
    if data[:4] != b"\xfa\x57\xc0\xde":
        raise ValueError(f"{path} is not a .pex file")
    _, user_start = read_string(data, 16)
    _, offset = read_string(data, user_start)
    _, offset = read_string(data, offset)
    packed = struct.pack(">H", len(LABEL)) + LABEL
    path.write_bytes(data[:user_start] + packed + packed + data[offset:])


if __name__ == "__main__":
    for pex in pathlib.Path(sys.argv[1]).glob("*.pex"):
        anonymize(pex)
        print("anonymized:", pex.name)
