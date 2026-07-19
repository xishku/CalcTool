"""FNV-1a 64-bit 哈希计算 — 零外部依赖"""

FNV_OFFSET = 0xcbf29ce484222325
FNV_PRIME  = 0x100000001b3

def hash_fnv1a(data):
    """对字节数据计算 FNV-1a 64-bit 哈希值"""
    h = FNV_OFFSET
    for byte in data:
        h ^= byte
        h = (h * FNV_PRIME) & 0xffffffffffffffff
    return h

def run_hash_fnv1a(data):
    return hash_fnv1a(data)
