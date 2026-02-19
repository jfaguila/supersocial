"""
API Checker — verifica el estado de configuración de cada plataforma.
Dice exactamente qué falta para que George pueda operar.
"""
from config.settings import get_settings
from tools_server.schemas import ApiHealthResponse, PlatformApiStatus


class ApiChecker:
    def __init__(self):
        self._s = get_settings()

    def check_all(self) -> ApiHealthResponse:
        platforms = [
            self._check_twitter(),
            self._check_tiktok(),
            self._check_linkedin(),
            self._check_instagram(),
        ]

        warnings = []
        for p in platforms:
            if not p.configured:
                warnings.append(
                    f"⚠️  {p.platform.upper()}: faltan credenciales — {', '.join(p.missing_keys)}"
                )
            elif not p.can_publish:
                warnings.append(
                    f"⚠️  {p.platform.upper()}: configurado solo lectura, no puede publicar"
                )

        if not self._s.openai_api_key:
            warnings.append("❌ OPENAI_API_KEY no configurada — George no puede generar contenido")

        any_platform_ready = any(p.configured for p in platforms)
        llm_ready = bool(self._s.openai_api_key)

        return ApiHealthResponse(
            overall_ready=any_platform_ready and llm_ready,
            platforms=platforms,
            llm_configured=llm_ready,
            llm_model=self._s.openai_model,
            database_configured=bool(self._s.database_url),
            redis_configured=bool(self._s.redis_url),
            warnings=warnings,
        )

    def _check_twitter(self) -> PlatformApiStatus:
        missing = []
        if not self._s.twitter_bearer_token:
            missing.append("TWITTER_BEARER_TOKEN")
        if not self._s.twitter_api_key:
            missing.append("TWITTER_API_KEY")
        if not self._s.twitter_api_secret:
            missing.append("TWITTER_API_SECRET")
        if not self._s.twitter_access_token:
            missing.append("TWITTER_ACCESS_TOKEN")
        if not self._s.twitter_access_secret:
            missing.append("TWITTER_ACCESS_SECRET")

        can_read = bool(self._s.twitter_bearer_token)
        can_publish = can_read and bool(self._s.twitter_api_key and self._s.twitter_access_token)

        return PlatformApiStatus(
            platform="twitter",
            configured=can_read,
            missing_keys=missing,
            can_read=can_read,
            can_publish=can_publish,
            notes="Bearer Token = leer tendencias. API Key + Access Token = publicar tweets.",
        )

    def _check_tiktok(self) -> PlatformApiStatus:
        missing = []
        if not self._s.tiktok_client_key:
            missing.append("TIKTOK_CLIENT_KEY")
        if not self._s.tiktok_client_secret:
            missing.append("TIKTOK_CLIENT_SECRET")
        if not self._s.tiktok_access_token:
            missing.append("TIKTOK_ACCESS_TOKEN")

        configured = bool(self._s.tiktok_client_key and self._s.tiktok_access_token)

        return PlatformApiStatus(
            platform="tiktok",
            configured=configured,
            missing_keys=missing,
            can_read=configured,
            can_publish=configured,
            notes="Requiere solicitar acceso a TikTok Research API + Content Posting API por separado.",
        )

    def _check_linkedin(self) -> PlatformApiStatus:
        missing = []
        if not self._s.linkedin_client_id:
            missing.append("LINKEDIN_CLIENT_ID")
        if not self._s.linkedin_client_secret:
            missing.append("LINKEDIN_CLIENT_SECRET")
        if not self._s.linkedin_access_token:
            missing.append("LINKEDIN_ACCESS_TOKEN")
        if not self._s.linkedin_person_urn:
            missing.append("LINKEDIN_PERSON_URN")

        configured = bool(self._s.linkedin_access_token and self._s.linkedin_person_urn)

        return PlatformApiStatus(
            platform="linkedin",
            configured=configured,
            missing_keys=missing,
            can_read=configured,
            can_publish=configured,
            notes="Access Token expira cada 60 días. Necesita refresco manual o con refresh_token.",
        )

    def _check_instagram(self) -> PlatformApiStatus:
        missing = []
        if not self._s.instagram_access_token:
            missing.append("INSTAGRAM_ACCESS_TOKEN")
        if not self._s.instagram_business_account_id:
            missing.append("INSTAGRAM_BUSINESS_ACCOUNT_ID")
        if not self._s.instagram_app_id:
            missing.append("INSTAGRAM_APP_ID")
        if not self._s.instagram_app_secret:
            missing.append("INSTAGRAM_APP_SECRET")

        configured = bool(
            self._s.instagram_access_token and self._s.instagram_business_account_id
        )

        return PlatformApiStatus(
            platform="instagram",
            configured=configured,
            missing_keys=missing,
            can_read=configured,
            can_publish=configured,
            notes="Requiere cuenta Business o Creator conectada a una página de Facebook.",
        )
