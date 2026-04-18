import unittest
from datetime import UTC, datetime

from app.domain.models import SourceFetchResult
from app.sources.x_posts.models import XPost
from app.sources.x_posts.service import X_POSTS_SOURCE_KEY, X_POSTS_SOURCE_NAME, XPostsSource


class StubXPostsClient:
    def fetch_posts(
        self,
        username: str,
        *,
        max_results: int,
        exclude_replies: bool,
        exclude_retweets: bool,
    ) -> list[XPost]:
        if username == "missing":
            return []
        self.last_call = {
            "username": username,
            "max_results": max_results,
            "exclude_replies": exclude_replies,
            "exclude_retweets": exclude_retweets,
        }
        return [
            XPost(
                id=f"{username}-1",
                author_id=f"id-{username}",
                username=username,
                text="New model launch\nwith details",
                created_at=datetime(2026, 4, 18, 10, 30, tzinfo=UTC),
                url=f"https://x.com/{username}/status/{username}-1",
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

    def test_fetch_sorts_newest_posts_first(self) -> None:
        class OrderedStubClient:
            def fetch_posts(self, username: str, *, max_results: int, exclude_replies: bool, exclude_retweets: bool) -> list[XPost]:
                return [
                    XPost(
                        id="older",
                        author_id="1",
                        username=username,
                        text="older post",
                        created_at=datetime(2026, 4, 17, 10, 30, tzinfo=UTC),
                        url=f"https://x.com/{username}/status/older",
                    ),
                    XPost(
                        id="newer",
                        author_id="1",
                        username=username,
                        text="newer post",
                        created_at=datetime(2026, 4, 18, 10, 30, tzinfo=UTC),
                        url=f"https://x.com/{username}/status/newer",
                    ),
                ]

        source = XPostsSource(
            enabled=True,
            client=OrderedStubClient(),
            usernames=("OpenAI",),
        )

        result = source.fetch()

        self.assertEqual([item.external_id for item in result.items], ["newer", "older"])


if __name__ == "__main__":
    unittest.main()
