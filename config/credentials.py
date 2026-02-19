"""
Credential manager — wraps settings and provides a unified interface.
In production, this can be extended to pull from AWS Secrets Manager,
HashiCorp Vault, or GCP Secret Manager.
"""
from dataclasses import dataclass
from typing import Optional

from .settings import Settings, get_settings


@dataclass(frozen=True)
class PlatformCredentials:
    platform: str
    is_configured: bool
    token: str = ""
    extra: dict = None  # type: ignore


class CredentialManager:
    def __init__(self, settings: Optional[Settings] = None):
        self._s = settings or get_settings()

    def twitter(self) -> PlatformCredentials:
        configured = bool(self._s.twitter_bearer_token and self._s.twitter_api_key)
        return PlatformCredentials(
            platform="twitter",
            is_configured=configured,
            token=self._s.twitter_bearer_token,
            extra={
                "api_key": self._s.twitter_api_key,
                "api_secret": self._s.twitter_api_secret,
                "access_token": self._s.twitter_access_token,
                "access_secret": self._s.twitter_access_secret,
            },
        )

    def tiktok(self) -> PlatformCredentials:
        configured = bool(self._s.tiktok_client_key and self._s.tiktok_access_token)
        return PlatformCredentials(
            platform="tiktok",
            is_configured=configured,
            token=self._s.tiktok_access_token,
            extra={
                "client_key": self._s.tiktok_client_key,
                "client_secret": self._s.tiktok_client_secret,
            },
        )

    def linkedin(self) -> PlatformCredentials:
        configured = bool(self._s.linkedin_access_token and self._s.linkedin_person_urn)
        return PlatformCredentials(
            platform="linkedin",
            is_configured=configured,
            token=self._s.linkedin_access_token,
            extra={
                "client_id": self._s.linkedin_client_id,
                "client_secret": self._s.linkedin_client_secret,
                "person_urn": self._s.linkedin_person_urn,
            },
        )

    def instagram(self) -> PlatformCredentials:
        configured = bool(
            self._s.instagram_access_token and self._s.instagram_business_account_id
        )
        return PlatformCredentials(
            platform="instagram",
            is_configured=configured,
            token=self._s.instagram_access_token,
            extra={
                "business_account_id": self._s.instagram_business_account_id,
                "app_id": self._s.instagram_app_id,
                "app_secret": self._s.instagram_app_secret,
            },
        )

    def get_configured_platforms(self) -> list[str]:
        platforms = []
        for cred_fn in [self.twitter, self.tiktok, self.linkedin, self.instagram]:
            cred = cred_fn()
            if cred.is_configured:
                platforms.append(cred.platform)
        return platforms
