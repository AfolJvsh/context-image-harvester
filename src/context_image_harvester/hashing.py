from __future__ import annotations

import hashlib
from functools import lru_cache

import numpy as np
from PIL import Image


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@lru_cache(maxsize=4)
def _dct_matrix(size: int) -> np.ndarray:
    matrix = np.empty((size, size), dtype=np.float64)
    factor = np.pi / (2.0 * size)
    scale0 = np.sqrt(1.0 / size)
    scale = np.sqrt(2.0 / size)
    for k in range(size):
        alpha = scale0 if k == 0 else scale
        for n in range(size):
            matrix[k, n] = alpha * np.cos((2 * n + 1) * k * factor)
    return matrix


def phash(image: Image.Image, hash_size: int = 8, highfreq_factor: int = 4) -> str:
    size = hash_size * highfreq_factor
    gray = image.convert("L").resize((size, size), Image.Resampling.LANCZOS)
    pixels = np.asarray(gray, dtype=np.float64)
    dct = _dct_matrix(size)
    transformed = dct @ pixels @ dct.T
    low = transformed[:hash_size, :hash_size]
    values = low.flatten()
    median = np.median(values[1:])
    bits = values > median
    number = 0
    for bit in bits:
        number = (number << 1) | int(bit)
    return f"{number:0{hash_size * hash_size // 4}x}"


def hamming(a: str, b: str) -> int:
    return (int(a, 16) ^ int(b, 16)).bit_count()
