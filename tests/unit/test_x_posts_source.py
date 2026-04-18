import unittest
from datetime import UTC, datetime

from app.domain.models import SourceFetchResult
from app.sources.x_posts.models import XPost, XUser
from app.sources.x_posts.service import X_POSTS_SOURCE_KEY, X_POSTS_SOURCE_NAME, XPostsSource


class StubXPostsClient:
    def lookup_user_by_username(self, username: str) -> XUser | None:
        if username == "missing":
            return None
        return XUser(id=f"id-{username}", username=username, name=username)

    def fetch_user_posts(
        self,
        user: XUser,
        *,
        max_results: int,
        exclude_replies: bool,
        exclude_retweets: bool,
    ) -> list[XPost]:
        self.last_call = {
            "username": user.username,
            "max_results": max_results,
            "exclude_replies": exclude_replies,
            "exclude_retweets": exclude_retweets,
        }
        return [
            XPost(
                id=f"{user.username}-1",
                author_id=user.id,
                username=user.username,
                text="New model launch\nwith details",
                created_at=datetime(2026, 4, 18, 10, 30, tzinfo=UTC),
            )
        ]


class XPostsSourceTestCase(unittest.TestCase):
    def test_fetch_wraps_posts_as_content_items(self) -> None:
        client = StubXPostsClient()
        source = XPostsSource(
            key=X_POSTS_SOURCE_KEY,
            name=X_POSTS_SOURCE_NAME,
            enabled=True,
            client=client,
            usernames=("OpenAI",),
            max_results_per_user=3,
            exclude_replies=True,
            exclude_retweets=True,
        )

        result = source.fetch()

        self.assertIsInstance(result, SourceFetchResult)
        self.assertEqual(result.source_key, X_POSTS_SOURCE_KEY)
        self.assertEqual(result.source_name, X_POSTS_SOURCE_NAME)
        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.items[0].title, "@OpenAI")
        self.assertEqual(result.items[0].source_name, X_POSTS_SOURCE_NAME)
        self.assertEqual(result.items[0].summary, "New model launch with details")
        self.assertEqual(result.items[0].url, "https://x.com/OpenAI/status/OpenAI-1")
        self.assertEqual(result.items[0].metadata["include_url"], "true")
        self.assertEqual(result.items[0].metadata["time"], "2026-04-18 10:30:00 UTC")
        self.assertEqual(client.last_call["max_results"], 3)
        self.assertTrue(client.last_call["exclude_replies"])
        self.assertTrue(client.last_call["exclude_retweets"])

    def test_fetch_skips_unknown_usernames(self) -> None:
        source = XPostsSource(
            enabled=True,
            client=StubXPostsClient(),
            usernames=("missing",),
        )

        result = source.fetch()

        self.assertEqual(result.items, [])


if __name__ == "__main__":
    unittest.main()
