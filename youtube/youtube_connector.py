"""
YouTube Data API v3 connector — Upload, metadata, and analytics.

Handles:
    - Resumable video upload (for large files)
    - Metadata setting (title, description, tags, category)
    - Thumbnail upload
    - AI content disclosure (self_declared_made_with_ai)
    - Privacy status management (unlisted → public scheduling)
    - Basic analytics fetching (views, likes, watch time)

Requires google-api-python-client and google-auth-oauthlib.
"""
import logging
import os
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

_YOUTUBE_UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
_YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3"
_YOUTUBE_OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"


@dataclass
class UploadResult:
    success: bool
    video_id: str = ""
    youtube_url: str = ""
    error: str = ""


@dataclass
class VideoAnalytics:
    views: int = 0
    likes: int = 0
    comments: int = 0
    watch_time_hours: float = 0.0
    avg_view_duration: float = 0.0
    ctr: float = 0.0


class YouTubeConnector:
    """
    YouTube Data API v3 connector for video upload and management.

    Usage:
        connector = YouTubeConnector(
            client_id="...",
            client_secret="...",
            refresh_token="...",
        )
        result = await connector.upload_video(
            video_path="/path/to/video.mp4",
            title="My Video",
            description="Description here",
            tags=["tag1", "tag2"],
            category_id="28",
        )
    """

    def __init__(
        self,
        client_id: str = "",
        client_secret: str = "",
        refresh_token: str = "",
    ):
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_token = refresh_token
        self._access_token: str = ""

    async def _ensure_access_token(self) -> None:
        """Refresh the OAuth2 access token using the refresh token."""
        if self._access_token:
            return

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                _YOUTUBE_OAUTH_TOKEN_URL,
                data={
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "refresh_token": self._refresh_token,
                    "grant_type": "refresh_token",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            self._access_token = data["access_token"]
            logger.debug("[youtube] access token refreshed")

    async def upload_video(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: list[str] | None = None,
        category_id: str = "28",
        privacy_status: str = "unlisted",
        made_for_kids: bool = False,
        is_ai_generated: bool = True,
        scheduled_publish_at: str | None = None,
    ) -> UploadResult:
        """
        Upload a video to YouTube using resumable upload.

        Args:
            video_path: Path to the MP4 file
            title: Video title
            description: Video description
            tags: List of tags
            category_id: YouTube category ID
            privacy_status: "public", "unlisted", or "private"
            made_for_kids: Whether the content is made for children
            is_ai_generated: Whether to flag as AI-generated content
            scheduled_publish_at: ISO 8601 datetime for scheduled publish (privacy must be "private")
        """
        await self._ensure_access_token()

        if not os.path.exists(video_path):
            return UploadResult(success=False, error=f"Video file not found: {video_path}")

        file_size = os.path.getsize(video_path)

        # Build video resource metadata
        body = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": (tags or [])[:30],
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": made_for_kids,
            },
        }

        # Schedule publishing if requested
        if scheduled_publish_at and privacy_status == "private":
            body["status"]["publishAt"] = scheduled_publish_at

        async with httpx.AsyncClient(timeout=600.0) as client:
            try:
                # Step 1: Initiate resumable upload
                headers = {
                    "Authorization": f"Bearer {self._access_token}",
                    "Content-Type": "application/json",
                    "X-Upload-Content-Length": str(file_size),
                    "X-Upload-Content-Type": "video/mp4",
                }
                init_resp = await client.post(
                    _YOUTUBE_UPLOAD_URL,
                    params={
                        "uploadType": "resumable",
                        "part": "snippet,status",
                    },
                    headers=headers,
                    json=body,
                )
                init_resp.raise_for_status()
                upload_url = init_resp.headers.get("Location")
                if not upload_url:
                    return UploadResult(success=False, error="No upload URL returned")

                # Step 2: Upload the video file
                with open(video_path, "rb") as f:
                    video_data = f.read()

                upload_resp = await client.put(
                    upload_url,
                    headers={
                        "Authorization": f"Bearer {self._access_token}",
                        "Content-Type": "video/mp4",
                        "Content-Length": str(file_size),
                    },
                    content=video_data,
                )
                upload_resp.raise_for_status()
                data = upload_resp.json()

                video_id = data.get("id", "")
                youtube_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else ""

                logger.info(f"[youtube] video uploaded: {video_id} → {youtube_url}")

                # Step 3: Set AI disclosure if requested
                if is_ai_generated and video_id:
                    await self._set_ai_disclosure(client, video_id)

                return UploadResult(
                    success=True,
                    video_id=video_id,
                    youtube_url=youtube_url,
                )

            except httpx.HTTPStatusError as e:
                error_msg = f"Upload failed: {e.response.status_code} {e.response.text[:300]}"
                logger.error(f"[youtube] {error_msg}")
                return UploadResult(success=False, error=error_msg)
            except Exception as e:
                logger.error(f"[youtube] upload error: {e}")
                return UploadResult(success=False, error=str(e))

    async def upload_thumbnail(
        self, video_id: str, thumbnail_path: str,
    ) -> bool:
        """Upload a custom thumbnail for a video."""
        await self._ensure_access_token()

        if not os.path.exists(thumbnail_path):
            logger.error(f"[youtube] thumbnail not found: {thumbnail_path}")
            return False

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                with open(thumbnail_path, "rb") as f:
                    image_data = f.read()

                resp = await client.post(
                    f"{_YOUTUBE_API_URL}/thumbnails/set",
                    params={"videoId": video_id},
                    headers={
                        "Authorization": f"Bearer {self._access_token}",
                        "Content-Type": "image/jpeg",
                    },
                    content=image_data,
                )
                resp.raise_for_status()
                logger.info(f"[youtube] thumbnail uploaded for {video_id}")
                return True

            except Exception as e:
                logger.error(f"[youtube] thumbnail upload failed: {e}")
                return False

    async def update_video_status(
        self, video_id: str, privacy_status: str,
    ) -> bool:
        """Update a video's privacy status (e.g., unlisted → public)."""
        await self._ensure_access_token()

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.put(
                    f"{_YOUTUBE_API_URL}/videos",
                    params={"part": "status"},
                    headers={
                        "Authorization": f"Bearer {self._access_token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "id": video_id,
                        "status": {"privacyStatus": privacy_status},
                    },
                )
                resp.raise_for_status()
                logger.info(f"[youtube] video {video_id} status → {privacy_status}")
                return True

            except Exception as e:
                logger.error(f"[youtube] status update failed: {e}")
                return False

    async def fetch_video_analytics(self, video_id: str) -> VideoAnalytics:
        """Fetch basic analytics for a video."""
        await self._ensure_access_token()

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(
                    f"{_YOUTUBE_API_URL}/videos",
                    params={
                        "part": "statistics",
                        "id": video_id,
                    },
                    headers={"Authorization": f"Bearer {self._access_token}"},
                )
                resp.raise_for_status()
                items = resp.json().get("items", [])
                if not items:
                    return VideoAnalytics()

                stats = items[0].get("statistics", {})
                return VideoAnalytics(
                    views=int(stats.get("viewCount", 0)),
                    likes=int(stats.get("likeCount", 0)),
                    comments=int(stats.get("commentCount", 0)),
                )

            except Exception as e:
                logger.error(f"[youtube] analytics fetch failed: {e}")
                return VideoAnalytics()

    async def _set_ai_disclosure(
        self, client: httpx.AsyncClient, video_id: str,
    ) -> None:
        """
        Set AI content disclosure on the video.
        Uses the YouTube API to mark content as AI-generated.
        """
        try:
            # First get the current video details
            get_resp = await client.get(
                f"{_YOUTUBE_API_URL}/videos",
                params={"part": "status", "id": video_id},
                headers={"Authorization": f"Bearer {self._access_token}"},
            )
            get_resp.raise_for_status()
            items = get_resp.json().get("items", [])
            if not items:
                return

            current_status = items[0].get("status", {})
            current_status["selfDeclaredMadeWithAi"] = True

            resp = await client.put(
                f"{_YOUTUBE_API_URL}/videos",
                params={"part": "status"},
                headers={
                    "Authorization": f"Bearer {self._access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "id": video_id,
                    "status": current_status,
                },
            )
            resp.raise_for_status()
            logger.info(f"[youtube] AI disclosure set for {video_id}")

        except Exception as e:
            logger.warning(f"[youtube] AI disclosure failed (non-fatal): {e}")
