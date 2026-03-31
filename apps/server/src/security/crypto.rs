use aes_gcm_siv::{
    Aes256GcmSiv, Nonce,
    aead::{Aead, KeyInit},
};
use argon2::Argon2;
use base64::{Engine as _, engine::general_purpose::URL_SAFE_NO_PAD};

use crate::app::error::AppError;

const ENCRYPTION_SALT: &[u8] = b"to-know-everything-master-key";

#[derive(Clone)]
pub struct CryptoContext {
    key: [u8; 32],
}

impl CryptoContext {
    pub fn new(master_password: &str) -> Result<Self, AppError> {
        let mut key = [0_u8; 32];
        Argon2::default()
            .hash_password_into(master_password.as_bytes(), ENCRYPTION_SALT, &mut key)
            .map_err(AppError::internal)?;

        Ok(Self { key })
    }

    pub fn encrypt(&self, plaintext: &str) -> Result<String, AppError> {
        let cipher = Aes256GcmSiv::new_from_slice(&self.key).map_err(AppError::internal)?;
        let mut nonce_bytes = [0_u8; 12];
        rand::fill(&mut nonce_bytes);

        let ciphertext = cipher
            .encrypt(Nonce::from_slice(&nonce_bytes), plaintext.as_bytes())
            .map_err(AppError::internal)?;

        let mut payload = Vec::with_capacity(nonce_bytes.len() + ciphertext.len());
        payload.extend_from_slice(&nonce_bytes);
        payload.extend_from_slice(&ciphertext);

        Ok(URL_SAFE_NO_PAD.encode(payload))
    }

    pub fn decrypt(&self, payload: &str) -> Result<String, AppError> {
        let decoded = URL_SAFE_NO_PAD
            .decode(payload)
            .map_err(AppError::internal)?;
        if decoded.len() < 13 {
            return Err(AppError::bad_request("Encrypted payload is invalid."));
        }

        let (nonce_bytes, ciphertext) = decoded.split_at(12);
        let cipher = Aes256GcmSiv::new_from_slice(&self.key).map_err(AppError::internal)?;
        let plaintext = cipher
            .decrypt(Nonce::from_slice(nonce_bytes), ciphertext)
            .map_err(AppError::internal)?;

        String::from_utf8(plaintext).map_err(AppError::internal)
    }
}
