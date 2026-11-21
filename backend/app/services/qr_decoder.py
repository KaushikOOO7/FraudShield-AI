import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Literal

from pydantic import model_validator

from backend.app.core.config import PROJECT_ROOT
from backend.app.core.errors import APIError
from backend.app.schemas.investigation import ContractModel


class DecodedImage(ContractModel):
    status: Literal["decoded", "no_qr_found", "multiple_qr_codes", "payload_too_large", "invalid_image"]
    content: str | None
    image_format: Literal["PNG", "JPEG"] | None

    @model_validator(mode="after")
    def actual_content(self):
        if self.status == "decoded" and (not self.content or len(self.content) > 5000):
            raise ValueError("Invalid decoded payload")
        if self.status != "decoded" and self.content is not None:
            raise ValueError("No payload may be substituted")
        return self


def decode_image(data: bytes) -> DecodedImage:
    with tempfile.TemporaryDirectory(prefix="fraudshield-qr-") as directory:
        path = Path(directory) / "upload.image"
        path.write_bytes(data)
        path.chmod(0o600)
        try:
            process = subprocess.run(
                [sys.executable, "-m", "backend.app.services.qr_worker", str(path)],
                cwd=PROJECT_ROOT, env={"PATH": os.defpath, "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"},
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10, check=False,
            )
            if process.returncode != 0 or len(process.stdout) > 65536:
                raise APIError(422, "image_processing_failed", "Image parsing did not complete within resource limits")
            result = DecodedImage.model_validate(json.loads(process.stdout))
        except subprocess.TimeoutExpired:
            raise APIError(422, "image_processing_timeout", "Image parsing timed out") from None
        except (ValueError, OSError):
            raise APIError(422, "image_processing_failed", "Image parsing failed") from None
    if result.status in ("invalid_image", "multiple_qr_codes", "payload_too_large"):
        raise APIError(422, result.status, "Use one readable QR code in a valid PNG or JPEG image with a bounded payload")
    return result
