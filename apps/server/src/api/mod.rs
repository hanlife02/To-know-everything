pub mod auth;
pub mod dashboard;
pub mod health;
pub mod settings;
pub mod tasks;

use axum::{
    Router,
    routing::{get, post},
};

use crate::app::state::SharedState;

pub fn router() -> Router<SharedState> {
    Router::new()
        .route("/health", get(health::health))
        .route("/auth/bootstrap-status", get(auth::bootstrap_status))
        .route("/auth/setup", post(auth::setup))
        .route("/auth/login", post(auth::login))
        .route("/auth/logout", post(auth::logout))
        .route("/auth/me", get(auth::me))
        .route("/dashboard/overview", get(dashboard::overview))
        .route(
            "/settings/accounts",
            get(settings::list_accounts).post(settings::create_account),
        )
        .route(
            "/settings/cookies",
            get(settings::list_cookie_profiles).post(settings::create_cookie_profile),
        )
        .route(
            "/settings/model-providers",
            get(settings::list_model_providers).post(settings::create_model_provider),
        )
        .route(
            "/settings/model-providers/discover-models",
            post(tasks::discover_models),
        )
        .route(
            "/tasks/collector-diagnostics",
            post(tasks::collector_diagnostics),
        )
        .route(
            "/settings/bark",
            get(settings::get_bark_config).put(settings::upsert_bark_config),
        )
        .route(
            "/settings/telegram",
            get(settings::get_telegram_config).put(settings::upsert_telegram_config),
        )
        .route("/tasks/manual-sync", post(tasks::manual_sync))
        .route("/tasks/test-telegram-push", post(tasks::test_telegram_push))
        .route("/tasks/runs", get(tasks::list_runs))
}
