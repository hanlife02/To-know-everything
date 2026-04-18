from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Protocol
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from app.sources.x_posts.models import XPost
from app.sources.x_posts.parser import (
    XWebGraphqlConfig,
    compact_json,
    extract_ct0,
    extract_graphql_config,
    extract_main_script_url,
    parse_timeline_posts,
    parse_user_rest_id,
)

USER_BY_SCREEN_NAME_FEATURES = {
    "hidden_profile_subscriptions_enabled": True,
    "profile_label_improvements_pcf_label_in_post_enabled": True,
    "responsive_web_profile_redirect_enabled": False,
    "rweb_tipjar_consumption_enabled": False,
    "verified_phone_label_enabled": False,
    "subscriptions_verification_info_is_identity_verified_enabled": True,
    "subscriptions_verification_info_verified_since_enabled": True,
    "highlights_tweets_tab_ui_enabled": True,
    "responsive_web_twitter_article_notes_tab_enabled": True,
    "subscriptions_feature_can_gift_premium": True,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "responsive_web_graphql_timeline_navigation_enabled": True,
}
USER_BY_SCREEN_NAME_FIELD_TOGGLES = {
    "withPayments": False,
    "withAuxiliaryUserLabels": True,
}
USER_TWEETS_FEATURES = {
    "rweb_video_screen_enabled": False,
    "rweb_cashtags_enabled": True,
    "profile_label_improvements_pcf_label_in_post_enabled": True,
    "responsive_web_profile_redirect_enabled": False,
    "rweb_tipjar_consumption_enabled": False,
    "verified_phone_label_enabled": False,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "premium_content_api_read_enabled": False,
    "communities_web_enable_tweet_community_results_fetch": True,
    "c9s_tweet_anatomy_moderator_badge_enabled": True,
    "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
    "responsive_web_grok_analyze_post_followups_enabled": True,
    "responsive_web_jetfuel_frame": True,
    "responsive_web_grok_share_attachment_enabled": True,
    "responsive_web_grok_annotations_enabled": True,
    "articles_preview_enabled": True,
    "responsive_web_edit_tweet_api_enabled": True,
    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
    "view_counts_everywhere_api_enabled": True,
    "longform_notetweets_consumption_enabled": True,
    "responsive_web_twitter_article_tweet_consumption_enabled": True,
    "content_disclosure_indicator_enabled": True,
    "content_disclosure_ai_generated_indicator_enabled": True,
    "responsive_web_grok_show_grok_translated_post": True,
    "responsive_web_grok_analysis_button_from_backend": True,
    "post_ctas_fetch_enabled": True,
    "freedom_of_speech_not_reach_fetch_enabled": True,
    "standardized_nudges_misinfo": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
    "longform_notetweets_rich_text_read_enabled": True,
    "longform_notetweets_inline_media_enabled": False,
    "responsive_web_grok_image_annotation_enabled": True,
    "responsive_web_grok_imagine_annotation_enabled": True,
    "responsive_web_grok_community_note_auto_translation_is_enabled": True,
    "responsive_web_enhance_cards_enabled": False,
}
USER_TWEETS_FIELD_TOGGLES = {
    "withArticleRichContentState": False,
    "withArticlePlainText": False,
    "withGrokAnalyze": False,
    "withDisallowedReplyControls": False,
}


class XPostsClient(Protocol):
    def fetch_posts(
        self,
        username: str,
        *,
        max_results: int,
        exclude_replies: bool,
        exclude_retweets: bool,
    ) -> list[XPost]:
        ...


@dataclass(slots=True)
class WebSessionXPostsClient:
    cookie_header: str
    base_url: str = "https://x.com"
    timeout_seconds: int = 20
    _graphql_config: XWebGraphqlConfig | None = field(default=None, init=False, repr=False)

    def fetch_posts(
        self,
        username: str,
        *,
        max_results: int,
        exclude_replies: bool,
        exclude_retweets: bool,
    ) -> list[XPost]:
        config = self._ensure_graphql_config()
        user_rest_id = self._fetch_user_rest_id(config, username)
        if not user_rest_id:
            return []
        payload = self._request_json(
            f"/i/api/graphql/{quote(config.user_tweets_query_id)}/UserTweets",
            params={
                "variables": compact_json(
                    {
                        "userId": user_rest_id,
                        "count": max_results,
                        "includePromotedContent": True,
                        "withQuickPromoteEligibilityTweetFields": True,
                        "withVoice": True,
                    }
                ),
                "features": compact_json(USER_TWEETS_FEATURES),
                "fieldToggles": compact_json(USER_TWEETS_FIELD_TOGGLES),
            },
            headers=self._build_api_headers(config.bearer_token, referer=f"{self.base_url.rstrip('/')}/{username}"),
        )
        posts = parse_timeline_posts(payload, username=username)
        return [
            post
            for post in posts
            if not (
                exclude_replies and self._is_reply(post, payload)
            ) and not (
                exclude_retweets and self._is_retweet(post, payload)
            )
        ]

    def _ensure_graphql_config(self) -> XWebGraphqlConfig:
        if self._graphql_config is None:
            page_html = self._fetch_text(f"/{quote('OpenAI', safe='')}")
            main_script_url = extract_main_script_url(page_html)
            main_script = self._fetch_absolute_text(main_script_url)
            self._graphql_config = extract_graphql_config(main_script, main_script_url=main_script_url)
        return self._graphql_config

    def _fetch_user_rest_id(self, config: XWebGraphqlConfig, username: str) -> str | None:
        payload = self._request_json(
            f"/i/api/graphql/{quote(config.user_by_screen_name_query_id)}/UserByScreenName",
            params={
                "variables": compact_json({"screen_name": username.lower(), "withGrokTranslatedBio": True}),
                "features": compact_json(USER_BY_SCREEN_NAME_FEATURES),
                "fieldToggles": compact_json(USER_BY_SCREEN_NAME_FIELD_TOGGLES),
            },
            headers=self._build_api_headers(config.bearer_token, referer=f"{self.base_url.rstrip('/')}/{username}"),
        )
        return parse_user_rest_id(payload)

    def _build_api_headers(self, bearer_token: str, *, referer: str) -> dict[str, str]:
        csrf_token = extract_ct0(self.cookie_header)
        return {
            "Authorization": f"Bearer {bearer_token}",
            "Cookie": self.cookie_header,
            "x-csrf-token": csrf_token,
            "x-twitter-client-language": "en",
            "x-twitter-active-user": "yes",
            "x-twitter-auth-type": "OAuth2Session",
            "content-type": "application/json",
            "Referer": referer,
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
            "Accept": "*/*",
        }

    def _request_json(self, path: str, *, params: dict[str, str], headers: dict[str, str]) -> dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}{path}?{urlencode(params)}"
        request = Request(url=url, headers=headers)
        with urlopen(request, timeout=self.timeout_seconds) as response:
            data = json.loads(response.read().decode("utf-8"))
        if not isinstance(data, dict):
            raise RuntimeError("x web timeline request returned unexpected payload shape")
        return data

    def _fetch_text(self, path: str) -> str:
        request = Request(
            url=f"{self.base_url.rstrip('/')}{path}",
            headers={
                "Cookie": self.cookie_header,
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            return response.read().decode("utf-8", errors="replace")

    def _fetch_absolute_text(self, url: str) -> str:
        request = Request(
            url=url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
                "Accept": "*/*",
            },
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            return response.read().decode("utf-8", errors="replace")

    def _is_reply(self, post: XPost, payload: dict[str, Any]) -> bool:
        legacy = _find_legacy_tweet_payload(payload, post.id)
        return bool(legacy and legacy.get("in_reply_to_status_id_str"))

    def _is_retweet(self, post: XPost, payload: dict[str, Any]) -> bool:
        legacy = _find_legacy_tweet_payload(payload, post.id)
        if not legacy:
            return False
        full_text = legacy.get("full_text")
        return isinstance(full_text, str) and full_text.startswith("RT @")


def _find_legacy_tweet_payload(payload: dict[str, Any], tweet_id: str) -> dict[str, Any] | None:
    stack: list[Any] = [payload]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            rest_id = current.get("rest_id")
            legacy = current.get("legacy")
            if rest_id == tweet_id and isinstance(legacy, dict):
                return legacy
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)
    return None
