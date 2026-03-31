use axum::{Json, extract::State};

use crate::{
    api::auth::AuthSession,
    app::{
        error::{AppError, AppResult},
        state::SharedState,
    },
    models::settings::DashboardOverviewResponse,
};

pub async fn overview(
    auth: AuthSession,
    State(state): State<SharedState>,
) -> AppResult<Json<DashboardOverviewResponse>> {
    let tracked_accounts: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM tracked_accounts")
        .fetch_one(&state.db)
        .await
        .map_err(AppError::internal)?;
    let cookie_profiles: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM cookie_profiles")
        .fetch_one(&state.db)
        .await
        .map_err(AppError::internal)?;
    let model_providers: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM model_providers")
        .fetch_one(&state.db)
        .await
        .map_err(AppError::internal)?;
    let contents: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM contents")
        .fetch_one(&state.db)
        .await
        .map_err(AppError::internal)?;
    let push_logs: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM push_logs")
        .fetch_one(&state.db)
        .await
        .map_err(AppError::internal)?;

    Ok(Json(DashboardOverviewResponse {
        app_name: state.config.app_name.clone(),
        user: auth.user,
        security_ready: state.crypto.is_some(),
        tracked_accounts,
        cookie_profiles,
        model_providers,
        contents,
        push_logs,
    }))
}
