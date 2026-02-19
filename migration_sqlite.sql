-- Migration: add subscriptions table (SQLite-friendly) 
CREATE TABLE IF NOT EXISTS subscriptions ( 
  id INTEGER PRIMARY KEY AUTOINCREMENT, 
  user_id INTEGER NOT NULL, 
  plan VARCHAR(64) NOT NULL, 
  status VARCHAR(32) DEFAULT 'PENDING', 
  payment_amount INTEGER, 
  payment_ref VARCHAR(128), 
  proof_path TEXT, 
  current_period_start TIMESTAMP, 
  current_period_end TIMESTAMP, 
  gateway_subscription_id VARCHAR(128), 
  cancel_at_period_end BOOLEAN DEFAULT 0, 
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
  approved_by INTEGER, 
  approved_at TIMESTAMP, 
  rejected_by INTEGER, 
  rejected_at TIMESTAMP, 
  reject_reason TEXT 
);
