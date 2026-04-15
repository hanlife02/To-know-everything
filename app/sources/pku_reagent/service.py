from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from app.config.settings import PkuReagentSettings
from app.domain.models import SourceFetchResult
from app.sources.base import SourceAdapter
from app.sources.pku_reagent.auth import CachedPkuReagentAuthenticator
from app.sources.pku_reagent.auth import IaaaOauthPkuReagentAuthenticator
from app.sources.pku_reagent.auth import PkuReagentAuthError
from app.sources.pku_reagent.auth import PkuReagentAuthenticator
from app.sources.pku_reagent.auth import PkuReagentSessionExpiredError
from app.sources.pku_reagent.auth import StaticPkuReagentAuthenticator
from app.sources.pku_reagent.client import HttpPkuReagentClient, PkuReagentClient
from app.sources.pku_reagent.models import PkuReagentOrderQuery
from app.sources.pku_reagent.parser import parse_orders, to_content_item


class PkuReagentOrderSource(SourceAdapter):
    def __init__(
        self,
        *,
        key: str,
        name: str,
        enabled: bool,
        authenticator: PkuReagentAuthenticator | None,
        client: PkuReagentClient | None,
        query: PkuReagentOrderQuery,
        base_url: str,
    ) -> None:
        self.key = key
        self.name = name
        self.enabled = enabled
        self.authenticator = authenticator
        self.client = client
        self.query = query
        self.base_url = base_url

    @classmethod
    def from_settings(cls, settings: PkuReagentSettings, *, session_cache_path: Path) -> "PkuReagentOrderSource":
        authenticator: PkuReagentAuthenticator | None = None
        client: PkuReagentClient | None = None
        if settings.enabled:
            authenticator = _build_authenticator(settings, session_cache_path=session_cache_path)
            client = HttpPkuReagentClient(base_url=settings.base_url)
        return cls(
            key="pku_reagent_orders",
            name="PKU Reagent Orders",
            enabled=settings.enabled,
            authenticator=authenticator,
            client=client,
            query=_build_order_query(settings),
            base_url=settings.base_url,
        )

    def fetch(self) -> SourceFetchResult:
        if self.client is None or self.authenticator is None:
            return SourceFetchResult(source_key=self.key, items=[])
        try:
            session = self.authenticator.authenticate()
            if session is None:
                return SourceFetchResult(source_key=self.key, items=[])
            try:
                rows = self.client.fetch_order_rows(session, self.query)
            except PkuReagentSessionExpiredError:
                session = self.authenticator.authenticate(force_refresh=True)
                if session is None:
                    return SourceFetchResult(source_key=self.key, items=[])
                rows = self.client.fetch_order_rows(session, self.query)
        except PkuReagentAuthError:
            return SourceFetchResult(source_key=self.key, items=[])
        orders = parse_orders(rows, base_url=self.base_url)
        items = [to_content_item(order, source_key=self.key) for order in orders]
        return SourceFetchResult(source_key=self.key, items=items)


def _build_authenticator(
    settings: PkuReagentSettings,
    *,
    session_cache_path: Path,
) -> PkuReagentAuthenticator:
    if settings.has_login_credentials():
        delegate: PkuReagentAuthenticator = IaaaOauthPkuReagentAuthenticator(
            base_url=settings.base_url,
            username=settings.username or "",
            password=settings.password,
            captcha_code=settings.captcha_code,
            sms_code=settings.sms_code,
            otp_code=settings.otp_code,
            iaaa_base_url=settings.iaaa_base_url,
        )
    else:
        delegate = StaticPkuReagentAuthenticator(
            username=settings.username or "",
            token=settings.token or "",
            cookie_header=settings.cookie_header or "",
        )
    return CachedPkuReagentAuthenticator(delegate=delegate, store_path=session_cache_path)


def _build_order_query(settings: PkuReagentSettings) -> PkuReagentOrderQuery:
    end_date = settings.end_date or date.today().isoformat()
    start_date = settings.start_date or (date.today() - timedelta(days=365)).isoformat()
    return PkuReagentOrderQuery(
        start_date=start_date,
        end_date=end_date,
        keyword=settings.keyword,
        group_code=settings.group_code,
        page_size=settings.page_size,
    )
