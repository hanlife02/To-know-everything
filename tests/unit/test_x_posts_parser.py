import unittest

from app.sources.x_posts.parser import (
    compact_json,
    extract_ct0,
    extract_graphql_config,
    extract_main_script_url,
    parse_timeline_posts,
    parse_user_rest_id,
)


class XPostsParserTestCase(unittest.TestCase):
    def test_extract_main_script_url_and_graphql_config(self) -> None:
        html = """
        <html><head>
          <script src="https://abs.twimg.com/responsive-web/client-web/main.123abc.js"></script>
        </head></html>
        """
        main_script = """
        something
        AAAAAAAAAAAAAAAAAAAAANRILgAAAAAATESTTOKEN
        more
        queryId:"user-id-1",operationName:"UserByScreenName"
        queryId:"user-tweets-2",operationName:"UserTweets"
        """

        main_script_url = extract_main_script_url(html)
        config = extract_graphql_config(main_script, main_script_url=main_script_url)

        self.assertEqual(main_script_url, "https://abs.twimg.com/responsive-web/client-web/main.123abc.js")
        self.assertEqual(config.user_by_screen_name_query_id, "user-id-1")
        self.assertEqual(config.user_tweets_query_id, "user-tweets-2")
        self.assertTrue(config.bearer_token.startswith("AAAAAAAAAAAAAAAAAAAAA"))

    def test_extract_ct0_requires_cookie_value(self) -> None:
        self.assertEqual(extract_ct0("auth_token=abc; ct0=csrf-token; lang=en"), "csrf-token")

    def test_parse_user_rest_id_and_timeline_posts(self) -> None:
        user_payload = {
            "data": {
                "user": {
                    "result": {
                        "rest_id": "4398626122",
                    }
                }
            }
        }
        timeline_payload = {
            "data": {
                "user": {
                    "result": {
                        "timeline": {
                            "timeline": {
                                "instructions": [
                                    {
                                        "type": "TimelineAddEntries",
                                        "entries": [
                                            {
                                                "entryId": "tweet-1",
                                                "content": {
                                                    "itemContent": {
                                                        "tweet_results": {
                                                            "result": {
                                                                "rest_id": "2042780052669239782",
                                                                "core": {"user_results": {"result": {"rest_id": "4398626122"}}},
                                                                "note_tweet": {
                                                                    "note_tweet_results": {
                                                                        "result": {
                                                                            "text": "Long note tweet body"
                                                                        }
                                                                    }
                                                                },
                                                                "legacy": {
                                                                    "created_at": "Sat Apr 11 01:41:32 +0000 2026",
                                                                    "full_text": "fallback text",
                                                                    "id_str": "2042780052669239782",
                                                                    "user_id_str": "4398626122",
                                                                },
                                                            }
                                                        }
                                                    }
                                                },
                                            }
                                        ],
                                    }
                                ]
                            }
                        }
                    }
                }
            }
        }

        self.assertEqual(parse_user_rest_id(user_payload), "4398626122")
        posts = parse_timeline_posts(timeline_payload, username="OpenAI")
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0].id, "2042780052669239782")
        self.assertEqual(posts[0].text, "Long note tweet body")
        self.assertEqual(posts[0].url, "https://x.com/OpenAI/status/2042780052669239782")

    def test_compact_json_removes_spaces(self) -> None:
        self.assertEqual(compact_json({"a": 1, "b": True}), '{"a":1,"b":true}')


if __name__ == "__main__":
    unittest.main()
