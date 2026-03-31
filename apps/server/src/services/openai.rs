use serde::Deserialize;

use crate::app::error::AppError;

pub async fn discover_models(base_url: &str, api_key: &str) -> Result<Vec<String>, AppError> {
    let normalized_base = base_url.trim().trim_end_matches('/');
    if normalized_base.is_empty() {
        return Err(AppError::bad_request("Base URL is required."));
    }
    if api_key.trim().is_empty() {
        return Err(AppError::bad_request("API key is required."));
    }

    let endpoint = format!("{normalized_base}/models");
    let response = reqwest::Client::new()
        .get(endpoint)
        .bearer_auth(api_key.trim())
        .header(reqwest::header::USER_AGENT, "tke-local/0.1")
        .send()
        .await
        .map_err(AppError::internal)?;

    if !response.status().is_success() {
        let status = response.status();
        let body = response.text().await.unwrap_or_default();
        let detail = if body.trim().is_empty() {
            format!("Model discovery failed with status {status}.")
        } else {
            format!("Model discovery failed with status {status}: {body}")
        };
        return Err(AppError::bad_request(detail));
    }

    let payload: ModelsEnvelope = response.json().await.map_err(AppError::internal)?;
    let mut models = payload
        .data
        .into_iter()
        .map(|entry| entry.id)
        .filter(|id| !id.trim().is_empty())
        .collect::<Vec<_>>();
    models.sort();
    models.dedup();

    Ok(models)
}

#[derive(Debug, Deserialize)]
struct ModelsEnvelope {
    data: Vec<ModelEntry>,
}

#[derive(Debug, Deserialize)]
struct ModelEntry {
    id: String,
}
