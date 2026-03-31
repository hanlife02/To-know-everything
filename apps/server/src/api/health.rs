use axum::{Json, extract::State};
use serde::Serialize;

use crate::app::state::SharedState;

pub async fn health(State(state): State<SharedState>) -> Json<HealthResponse> {
    Json(HealthResponse {
        status: "ok",
        app_name: state.config.app_name.clone(),
        version: env!("CARGO_PKG_VERSION"),
    })
}

#[derive(Debug, Serialize)]
pub struct HealthResponse {
    pub status: &'static str,
    pub app_name: String,
    pub version: &'static str,
}
