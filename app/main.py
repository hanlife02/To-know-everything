from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.auth import require_api_key
from app.config import Settings, get_settings
from app.models import AggregatedResponse, FeedKind, Platform
from app.services.aggregator import AggregatorService

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "web" / "templates"))


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "web" / "static")), name="static")
    app.state.aggregator = AggregatorService(settings)

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "app_name": settings.app_name,
                "default_limit": settings.default_limit,
                "platforms": [platform.value for platform in Platform],
                "feed_kinds": [feed_kind.value for feed_kind in FeedKind],
            },
        )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/content", response_model=AggregatedResponse, dependencies=[Depends(require_api_key)])
    async def get_content(
        request: Request,
        platforms: list[Platform] | None = Query(default=None),
        feed_kinds: list[FeedKind] | None = Query(default=None),
        categories: list[str] | None = Query(default=None),
        limit: int = Query(default=settings.default_limit, ge=1, le=30),
        app_settings: Settings = Depends(get_settings),
    ) -> AggregatedResponse:
        selected_platforms = platforms or list(Platform)
        selected_feed_kinds = feed_kinds or list(FeedKind)
        aggregator: AggregatorService = (request.app.state.aggregator if request else AggregatorService(app_settings))
        response = await aggregator.fetch(selected_platforms, selected_feed_kinds, limit)
        if categories:
            response.items = [item for item in response.items if item.category in categories]
            response.total = len(response.items)
            response.categories = sorted({item.category for item in response.items})
        return response

    return app


app = create_app()
