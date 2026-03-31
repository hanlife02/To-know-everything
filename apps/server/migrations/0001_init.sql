CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  token_hash TEXT NOT NULL UNIQUE,
  expires_at INTEGER NOT NULL,
  created_at INTEGER NOT NULL,
  last_seen_at INTEGER NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tracked_accounts (
  id TEXT PRIMARY KEY,
  platform TEXT NOT NULL,
  display_name TEXT NOT NULL,
  account_handle TEXT NOT NULL,
  profile_url TEXT,
  notes TEXT,
  is_active INTEGER NOT NULL DEFAULT 1,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  UNIQUE(platform, account_handle)
);

CREATE TABLE IF NOT EXISTS cookie_profiles (
  id TEXT PRIMARY KEY,
  label TEXT NOT NULL,
  platform TEXT NOT NULL,
  encrypted_cookie TEXT NOT NULL,
  cookie_preview TEXT NOT NULL,
  is_active INTEGER NOT NULL DEFAULT 1,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS model_providers (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  base_url TEXT NOT NULL,
  encrypted_api_key TEXT NOT NULL,
  api_key_preview TEXT NOT NULL,
  summary_model TEXT,
  translation_model TEXT,
  ocr_model TEXT,
  transcription_model TEXT,
  understanding_model TEXT,
  is_default INTEGER NOT NULL DEFAULT 0,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS bark_configs (
  id TEXT PRIMARY KEY,
  label TEXT NOT NULL,
  server_url TEXT NOT NULL,
  encrypted_device_key TEXT NOT NULL,
  device_key_preview TEXT NOT NULL,
  is_enabled INTEGER NOT NULL DEFAULT 1,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  cron_expression TEXT,
  is_enabled INTEGER NOT NULL DEFAULT 1,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS job_runs (
  id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL,
  status TEXT NOT NULL,
  started_at INTEGER NOT NULL,
  finished_at INTEGER,
  error_message TEXT,
  FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS contents (
  id TEXT PRIMARY KEY,
  platform TEXT NOT NULL,
  account_id TEXT NOT NULL,
  content_id TEXT NOT NULL,
  title TEXT,
  body_text TEXT,
  translated_text TEXT,
  ocr_text TEXT,
  transcript_text TEXT,
  video_understanding TEXT,
  source_url TEXT,
  published_at INTEGER,
  raw_payload TEXT,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  UNIQUE(platform, account_id, content_id)
);

CREATE TABLE IF NOT EXISTS content_comments (
  id TEXT PRIMARY KEY,
  content_row_id TEXT NOT NULL,
  author_name TEXT,
  like_count INTEGER NOT NULL DEFAULT 0,
  body_text TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  FOREIGN KEY (content_row_id) REFERENCES contents(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS content_assets (
  id TEXT PRIMARY KEY,
  content_row_id TEXT NOT NULL,
  asset_type TEXT NOT NULL,
  source_url TEXT,
  text_output TEXT,
  created_at INTEGER NOT NULL,
  FOREIGN KEY (content_row_id) REFERENCES contents(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ai_results (
  id TEXT PRIMARY KEY,
  content_row_id TEXT NOT NULL,
  summary_short TEXT,
  summary_medium TEXT,
  translated_text TEXT,
  keywords TEXT,
  importance_score REAL,
  push_text TEXT,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  FOREIGN KEY (content_row_id) REFERENCES contents(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS push_logs (
  id TEXT PRIMARY KEY,
  content_row_id TEXT,
  channel TEXT NOT NULL,
  status TEXT NOT NULL,
  message_preview TEXT,
  error_message TEXT,
  pushed_at INTEGER NOT NULL,
  FOREIGN KEY (content_row_id) REFERENCES contents(id) ON DELETE SET NULL
);
