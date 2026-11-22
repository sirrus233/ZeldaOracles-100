"""Write and apply the SourceRead/TargetRead BPS commands used by this project."""

from itertools import groupby
from struct import pack, unpack
from zlib import crc32



def encode_number(number):
    result = bytearray()
    while number >= 0x80:
        result.append(number & 0x7F)
        number = (number >> 7) - 1
    result.append(number | 0x80)
    return result


def make_patch(base, target):
    if len(base) != len(target):
        raise ValueError('This patch writer expects equal-size Oracle ROMs')
    result = bytearray(b'BPS1')
    for length in (len(base), len(target), 0):
        result.extend(encode_number(length))
    position = 0
    for different, run in groupby(a != b for a, b in zip(base, target)):
        length = sum(1 for _ in run)
        result.extend(encode_number(((length - 1) << 2) | different))
        if different:
            result.extend(target[position:position + length])
        position += length
    result.extend(pack('<II', crc32(base), crc32(target)))
    result.extend(pack('<I', crc32(result)))
    return result


def apply_patch(patch, base):
    """Verify and apply the two BPS commands emitted by this writer."""
    if patch[:4] != b'BPS1' or len(patch) < 16:
        raise ValueError('Invalid BPS patch')
    base_crc, target_crc, patch_crc = unpack('<III', patch[-12:])
    if crc32(base) != base_crc or crc32(patch[:-4]) != patch_crc:
        raise ValueError('Patch or base ROM checksum mismatch')
    position = 4

    def read_number():
        nonlocal position
        value, place = 0, 1
        while position < len(patch) - 12:
            byte = patch[position]
            position += 1
            value += (byte & 0x7F) * place
            if byte & 0x80:
                return value
            place *= 0x80
            value += place
        raise ValueError('Incomplete BPS number')

    source_size = read_number()
    output_size = read_number()
    metadata_size = read_number()
    position += metadata_size
    if source_size != len(base):
        raise ValueError('Incorrect base ROM size')

    output = bytearray()
    while len(output) < output_size:
        command = read_number()
        length = (command >> 2) + 1
        if command & 3 == 0:
            output.extend(base[len(output):len(output) + length])
        elif command & 3 == 1:
            output.extend(patch[position:position + length])
            position += length
        else:
            raise ValueError('Unexpected BPS command')
    if len(output) != output_size or crc32(output) != target_crc or position != len(patch) - 12:
        raise ValueError('Patched ROM checksum or length mismatch')
    return bytes(output)

