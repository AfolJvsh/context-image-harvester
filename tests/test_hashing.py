from PIL import Image, ImageDraw

from context_image_harvester.hashing import hamming, phash, sha256_bytes


def test_sha_and_phash_are_stable():
    image = Image.new("RGB", (128, 128), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 20, 80, 80), fill="black")
    first = phash(image)
    second = phash(image.copy())
    assert first == second
    assert hamming(first, second) == 0
    assert len(first) == 16
    assert sha256_bytes(b"abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
