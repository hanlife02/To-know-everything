use std::{
    collections::HashSet,
    env,
    error::Error,
    ffi::{OsStr, OsString},
    io::ErrorKind,
};

mod api;
mod app;
mod collectors;
mod jobs;
mod models;
mod repos;
mod security;
mod services;

use app::{config::AppConfig, state::AppState};
use tracing::info;
use tracing_subscriber::{EnvFilter, layer::SubscriberExt, util::SubscriberInitExt};

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    load_environment().map_err(std::io::Error::other)?;

    tracing_subscriber::registry()
        .with(
            EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "tke_server=info,tower_http=info".into()),
        )
        .with(tracing_subscriber::fmt::layer().with_target(false))
        .init();

    let config = AppConfig::from_env().map_err(std::io::Error::other)?;
    let state = AppState::initialize(config)
        .await
        .map_err(|err| std::io::Error::other(format!("failed to initialize state: {err}")))?;
    let app = app::build_router(state.clone());

    let listener = tokio::net::TcpListener::bind(&state.config.server_addr)
        .await
        .map_err(|err| std::io::Error::other(format!("failed to bind server socket: {err}")))?;

    info!(address = %state.config.server_addr, "server listening");

    axum::serve(listener, app)
        .await
        .map_err(|err| std::io::Error::other(format!("server exited with error: {err}")))?;

    Ok(())
}

fn load_environment() -> Result<(), String> {
    let preserved_keys = env::vars_os()
        .map(|(key, _)| key)
        .collect::<HashSet<OsString>>();

    load_env_file(".env", &preserved_keys).map_err(|error| format!(".env: {error}"))?;
    load_env_file(".env.local", &preserved_keys)
        .map_err(|error| format!(".env.local: {error}"))?;

    let runtime_env = env::var("TKE_ENV")
        .ok()
        .map(|value| value.trim().to_string())
        .filter(|value| !value.is_empty())
        .unwrap_or_else(default_runtime_env);

    load_env_file(&format!(".env.{runtime_env}"), &preserved_keys)
        .map_err(|error| format!(".env.{runtime_env}: {error}"))?;
    load_env_file(&format!(".env.{runtime_env}.local"), &preserved_keys)
        .map_err(|error| format!(".env.{runtime_env}.local: {error}"))?;

    Ok(())
}

fn default_runtime_env() -> String {
    if cfg!(debug_assertions) {
        "development".to_string()
    } else {
        "production".to_string()
    }
}

fn load_env_file(filename: &str, preserved_keys: &HashSet<OsString>) -> Result<(), dotenvy::Error> {
    let iter = match dotenvy::from_filename_iter(filename) {
        Ok(iter) => iter,
        Err(dotenvy::Error::Io(error)) if error.kind() == ErrorKind::NotFound => return Ok(()),
        Err(error) => return Err(error),
    };

    for item in iter {
        let (key, value) = item?;
        if preserved_keys.contains(OsStr::new(&key)) {
            continue;
        }

        // SAFETY: the process environment is initialized before the Tokio runtime starts.
        unsafe {
            env::set_var(&key, &value);
        }
    }

    Ok(())
}
