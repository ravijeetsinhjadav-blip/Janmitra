"""JanMitra Assist - OTP Service Deprecation Stub

OTP authentication has been fully removed from JanMitra Assist in favor of
strict Email + Password authentication with Argon2id cryptographic hashing.
"""

from fastapi import HTTPException, status


class OTPService:
    """Deprecated service stub."""

    @staticmethod
    def generate_and_send_otp(*args, **kwargs):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="OTP authentication has been deprecated and removed. Please use Email + Password authentication.",
        )

    @staticmethod
    def verify_otp(*args, **kwargs):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="OTP authentication has been deprecated and removed. Please use Email + Password authentication.",
        )
