use std::{fs, str::FromStr, sync::Arc};

use sqlx::{
    SqlitePool,
    sqlite::{SqliteConnectOptions, SqlitePoolOptions},
};

use crate::{
    app::{config::AppConfig, error::AppError},
    security::crypto::CryptoContext,
};

pub type SharedState = Arc<AppState>;

#[derive(Clone)]
pub struct AppState {
    pub config: AppConfig,
    pub db: SqlitePool,
    pub crypto: Option<CryptoContext>,
}

impl AppState {
    pub async fn initialize(config: AppConfig) -> Result<SharedState, AppError> {
        if let Some(parent) = config.database_path.parent() {
            fs::create_dir_all(parent).map_err(AppError::internal)?;
        }

        let connect_options = SqliteConnectOptions::from_str(&config.database_url())
            .map_err(AppError::internal)?
            .create_if_missing(true)
            .foreign_keys(true);

        let db = SqlitePoolOptions::new()
            .max_connections(5)
            .connect_with(connect_options)
            .await
            .map_err(AppError::internal)?;

        sqlx::query("PRAGMA journal_mode = WAL;")
            .execute(&db)
            .await
            .map_err(AppError::internal)?;

        sqlx::migrate!("./migrations")
            .run(&db)
            .await
            .map_err(AppError::internal)?;

        let crypto = config
            .master_password
            .as_deref()
            .map(CryptoContext::new)
            .transpose()?;

        Ok(Arc::new(Self { config, db, crypto }))
    }
}
