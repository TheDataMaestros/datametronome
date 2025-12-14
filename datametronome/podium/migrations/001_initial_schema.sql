-- Migration: 001_initial_schema
-- Description: Initial database schema for DataMetronome Podium
-- Date: 2024-10-03

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- Staves (Data Sources) table
CREATE TABLE IF NOT EXISTS staves (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    data_source_type TEXT NOT NULL,
    connection_config TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_staves_name ON staves(name);
CREATE INDEX IF NOT EXISTS idx_staves_type ON staves(data_source_type);
CREATE INDEX IF NOT EXISTS idx_staves_active ON staves(is_active);

-- Clefs (Data Quality Checks) table
CREATE TABLE IF NOT EXISTS clefs (
    id TEXT PRIMARY KEY,
    stave_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    check_type TEXT NOT NULL,
    config TEXT NOT NULL,
    schedule TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (stave_id) REFERENCES staves (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_clefs_stave_id ON clefs(stave_id);
CREATE INDEX IF NOT EXISTS idx_clefs_type ON clefs(check_type);
CREATE INDEX IF NOT EXISTS idx_clefs_active ON clefs(is_active);

-- Checks (Check Run Results) table
CREATE TABLE IF NOT EXISTS checks (
    id TEXT PRIMARY KEY,
    stave_id TEXT NOT NULL,
    clef_id TEXT NOT NULL,
    check_type TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT,
    details TEXT,
    timestamp TEXT NOT NULL,
    execution_time REAL,
    anomalies_count INTEGER DEFAULT 0,
    severity TEXT DEFAULT 'medium',
    FOREIGN KEY (stave_id) REFERENCES staves (id) ON DELETE CASCADE,
    FOREIGN KEY (clef_id) REFERENCES clefs (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_checks_stave_id ON checks(stave_id);
CREATE INDEX IF NOT EXISTS idx_checks_clef_id ON checks(clef_id);
CREATE INDEX IF NOT EXISTS idx_checks_timestamp ON checks(timestamp);
CREATE INDEX IF NOT EXISTS idx_checks_status ON checks(status);

-- Anomalies table
CREATE TABLE IF NOT EXISTS anomalies (
    id TEXT PRIMARY KEY,
    check_id TEXT NOT NULL,
    table_name TEXT,
    column_name TEXT,
    anomaly_type TEXT NOT NULL,
    description TEXT,
    severity TEXT DEFAULT 'medium',
    detected_at TEXT NOT NULL,
    data_sample TEXT,
    resolution_status TEXT DEFAULT 'investigating',
    FOREIGN KEY (check_id) REFERENCES checks (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_anomalies_check_id ON anomalies(check_id);
CREATE INDEX IF NOT EXISTS idx_anomalies_type ON anomalies(anomaly_type);
CREATE INDEX IF NOT EXISTS idx_anomalies_severity ON anomalies(severity);
CREATE INDEX IF NOT EXISTS idx_anomalies_status ON anomalies(resolution_status);
CREATE INDEX IF NOT EXISTS idx_anomalies_detected_at ON anomalies(detected_at);

-- Migration tracking table
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TEXT NOT NULL
);
