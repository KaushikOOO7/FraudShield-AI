"""Disposable, resource-limited QR image parser. No downloads or execution of content."""
import io
import json
import resource
import sys
import warnings
from pathlib import Path


def decode(path):
    resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
    resource.setrlimit(resource.RLIMIT_AS, (1536 * 1024 * 1024, 1536 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_FSIZE, (8 * 1024 * 1024, 8 * 1024 * 1024))
    import cv2
    import numpy as np
    from PIL import Image
    cv2.setNumThreads(1)

    Image.MAX_IMAGE_PIXELS = 10_000_000
    warnings.simplefilter("error", Image.DecompressionBombWarning)
    data = Path(path).read_bytes()
    with Image.open(io.BytesIO(data)) as image:
        if image.format not in ("PNG", "JPEG") or image.width * image.height > 10_000_000:
            raise ValueError("Unsupported image")
        image_format = image.format
        image.verify()
    with Image.open(io.BytesIO(data)) as image:
        rgb = np.asarray(image.convert("RGB"))
    image = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    detector = cv2.QRCodeDetector()
    success, payloads, _, _ = detector.detectAndDecodeMulti(image)
    if success:
        decoded = list(dict.fromkeys(value for value in payloads if value))
    else:
        payload, _, _ = detector.detectAndDecode(image)
        decoded = [payload] if payload else []
    if len(decoded) > 1:
        return {"status": "multiple_qr_codes", "content": None, "image_format": image_format}
    if decoded and len(decoded[0]) > 5000:
        return {"status": "payload_too_large", "content": None, "image_format": image_format}
    return {"status": "decoded" if decoded else "no_qr_found", "content": decoded[0] if decoded else None, "image_format": image_format}


if __name__ == "__main__":
    try:
        print(json.dumps(decode(sys.argv[1]), ensure_ascii=True))
    except Exception:
        print(json.dumps({"status": "invalid_image", "content": None, "image_format": None}))
