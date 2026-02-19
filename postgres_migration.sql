-- Migration: add subscriptions table (Postgres)
CREATE TYPE IF NOT EXISTS subscription_status AS ENUM ('PENDING','ACTIVE','PAST_DUE','CANCELLED','EXPIRED');

CREATE TABLE IF NOT EXISTS subscriptions (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  plan VARCHAR(64) NOT NULL,
  status subscription_status DEFAULT 'PENDING',
  payment_amount INTEGER,
  payment_ref VARCHAR(128),
  proof_path TEXT,
  current_period_start TIMESTAMP,
  current_period_end TIMESTAMP,
  gateway_subscription_id VARCHAR(128),
  cancel_at_period_end BOOLEAN DEFAULT false,
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),
  approved_by INTEGER,
  approved_at TIMESTAMP,
  rejected_by INTEGER,
  rejected_at TIMESTAMP,
  reject_reason TEXT
);
