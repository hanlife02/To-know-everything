CREATE TABLE IF NOT EXISTS telegram_configs (
  id TEXT PRIMARY KEY,
  label TEXT NOT NULL,
  api_base_url TEXT NOT NULL,
  chat_id TEXT NOT NULL,
  encrypted_bot_token TEXT NOT NULL,
  bot_token_preview TEXT NOT NULL,
  is_enabled INTEGER NOT NULL DEFAULT 1,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);
