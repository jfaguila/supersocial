"""
Shared test fixtures for SuperSocial.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    repo.get_all_weights = AsyncMock(return_value={})
    repo.get_weight = AsyncMock(return_value=1.0)
    repo.set_weight = AsyncMock()
    repo.get_top_hooks = AsyncMock(return_value=[])
    repo.get_top_triggers = AsyncMock(return_value=[])
    repo.get_growth_history = AsyncMock(return_value=[])
    repo.get_post_by_hash = AsyncMock(return_value=None)
    repo.create_post = AsyncMock(return_value=MagicMock(id="test-post-id"))
    repo.upsert_hook_pattern = AsyncMock()
    repo.log = AsyncMock()
    return repo


@pytest.fixture
def sample_trend_posts():
    from data_layer.base_connector import TrendPost
    return [
        TrendPost(
            platform="twitter",
            post_id=f"post_{i}",
            author_id=f"author_{i}",
            author_username=f"user_{i}",
            author_follower_count=10000,
            content_text=f"Stop trading your time for money. Here are 5 ways to build passive income: {i}",
            content_type="text",
            published_at=1700000000 + i * 3600,
            likes=1000 + i * 100,
            comments=50 + i * 10,
            shares=200 + i * 20,
            impressions=50000,
        )
        for i in range(20)
    ]
