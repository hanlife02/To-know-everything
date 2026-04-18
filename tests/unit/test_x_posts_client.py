import unittest
from unittest.mock import patch

from app.sources.x_posts.client import WebSessionXPostsClient
from app.sources.x_posts.parser import XWebGraphqlConfig


class WebSessionXPostsClientTestCase(unittest.TestCase):
    def test_build_api_headers_uses_cookie_session_and_csrf(self) -> None:
        client = WebSessionXPostsClient(cookie_header="auth_token=abc; ct0=csrf-token", base_url="https://x.com")

        headers = client._build_api_headers("AAAAAAAAAAAAAAAAAAAAATEST", referer="https://x.com/OpenAI")

        self.assertEqual(headers["Cookie"], "auth_token=abc; ct0=csrf-token")
        self.assertEqual(headers["x-csrf-token"], "csrf-token")
        self.assertEqual(headers["Authorization"], "Bearer AAAAAAAAAAAAAAAAAAAAATEST")
        self.assertEqual(headers["x-twitter-auth-type"], "OAuth2Session")

    def test_ensure_graphql_config_uses_openai_bootstrap_page(self) -> None:
        client = WebSessionXPostsClient(cookie_header="auth_token=abc; ct0=csrf-token", base_url="https://x.com")
        html = '<script src="https://abs.twimg.com/responsive-web/client-web/main.123abc.js"></script>'
        script = 'AAAAAAAAAAAAAAAAAAAAATEST queryId:"screen",operationName:"UserByScreenName" queryId:"tweets",operationName:"UserTweets"'
        calls: list[str] = []

        def fake_fetch_text(path: str) -> str:
            calls.append(path)
            return html

        def fake_fetch_absolute_text(url: str) -> str:
            calls.append(url)
            return script

        with patch.object(WebSessionXPostsClient, "_fetch_text", autospec=True, side_effect=lambda self, path: fake_fetch_text(path)):
            with patch.object(WebSessionXPostsClient, "_fetch_absolute_text", autospec=True, side_effect=lambda self, url: fake_fetch_absolute_text(url)):
                config = client._ensure_graphql_config()

        self.assertIsInstance(config, XWebGraphqlConfig)
        self.assertEqual(config.user_by_screen_name_query_id, "screen")
        self.assertEqual(config.user_tweets_query_id, "tweets")
        self.assertEqual(calls[0], "/OpenAI")


if __name__ == "__main__":
    unittest.main()
