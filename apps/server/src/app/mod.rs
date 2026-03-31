pub mod config;
pub mod error;
pub mod state;

use axum::{
    Router,
    http::{HeaderValue, Method, header::CONTENT_TYPE},
    routing::get,
};
use tower_http::{
    cors::{AllowOrigin, CorsLayer},
    trace::TraceLayer,
};

use crate::{api, app::state::SharedState};

pub fn build_router(state: SharedState) -> Router {
    let allowed_origins = state
        .config
        .web_origins
        .iter()
        .filter_map(|origin| HeaderValue::from_str(origin).ok())
        .collect::<Vec<_>>();

    let cors = CorsLayer::new()
        .allow_origin(AllowOrigin::list(allowed_origins))
        .allow_methods([Method::GET, Method::POST, Method::PUT, Method::OPTIONS])
        .allow_headers([CONTENT_TYPE])
        .allow_credentials(true);

    Router::new()
        .route("/", get(root))
        .nest("/api", api::router())
        .layer(TraceLayer::new_for_http())
        .layer(cors)
        .with_state(state)
}

async fn root() -> &'static str {
    "To Know Everything server"
}
