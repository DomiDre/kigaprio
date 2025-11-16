"""Health check endpoints."""

import json
from pathlib import Path

from fastapi import APIRouter

router = APIRouter()


@router.get(
    "/health",
    status_code=200,
    summary="Health Check",
    description="Check if the API is running and healthy",
)
async def health_check():
    """Health check endpoint."""
    return


@router.get(
    "/build-info",
    status_code=200,
    summary="Build Information",
    description="Get build and version information for verification",
)
async def build_info():
    """Return build information for transparency and verification.

    SECURITY WARNING: This endpoint returns metadata embedded in the image.
    A malicious actor could fake this data. For TRUE verification:
    1. Get the actual running image digest (docker inspect or K8s API)
    2. Verify that digest's signature with: cosign verify <image>@<digest>
    3. Check the provenance attestation for the commit SHA

    This endpoint is useful for convenience and transparency, but NOT
    sufficient for cryptographic verification.
    """
    build_info_file = Path("/app/build_info.json")

    # Default fallback if file doesn't exist (development mode)
    default_info = {
        "version": "development",
        "commit": "unknown",
        "build_date": "unknown",
        "source_url": "https://github.com/DomiDre/priotag",
        "security_warning": "This metadata can be forged. Verify the image digest externally.",
    }

    if build_info_file.exists():
        try:
            with open(build_info_file, "r") as f:
                info = json.load(f)
                info["security_warning"] = (
                    "This metadata can be forged. For true verification, "
                    "check the running container's image digest and verify "
                    "its signature with cosign."
                )
                info["verification_instructions"] = (
                    "https://github.com/DomiDre/priotag/blob/main/VERIFICATION.md#true-verification"
                )
                return info
        except Exception:
            return default_info

    return default_info
