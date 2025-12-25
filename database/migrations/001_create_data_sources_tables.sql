-- Миграция 001: Создание таблиц для управления источниками данных и целостностью

-- Таблица источников данных
CREATE TABLE IF NOT EXISTS data_sources (
    id SERIAL PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    source_type VARCHAR(50),  -- api, file, web, registry
    domain VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending',  -- pending, downloading, completed, failed, partial
    total_records INTEGER,
    downloaded_records INTEGER DEFAULT 0,
    last_successful_download TIMESTAMP,
    last_attempt TIMESTAMP,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_status ON data_sources(status);
CREATE INDEX IF NOT EXISTS idx_source_type ON data_sources(source_type);
CREATE INDEX IF NOT EXISTS idx_domain ON data_sources(domain);

-- Таблица для проверки целостности данных
CREATE TABLE IF NOT EXISTS data_integrity (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES data_sources(id) ON DELETE CASCADE,
    record_id TEXT,
    content_hash VARCHAR(64) NOT NULL,
    original_hash VARCHAR(64),  -- Хеш из исходного источника
    verification_status VARCHAR(50),  -- verified, mismatch, missing
    last_verified TIMESTAMP,
    differences JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_content_hash ON data_integrity(content_hash);
CREATE INDEX IF NOT EXISTS idx_source_record ON data_integrity(source_id, record_id);
CREATE INDEX IF NOT EXISTS idx_verification_status ON data_integrity(verification_status);

-- Таблица для хранения снимков исходных данных
CREATE TABLE IF NOT EXISTS source_snapshots (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES data_sources(id) ON DELETE CASCADE,
    snapshot_date TIMESTAMP DEFAULT NOW(),
    total_records INTEGER,
    records_hash VARCHAR(64),  -- Хеш всех записей вместе
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_snapshot_source ON source_snapshots(source_id);
CREATE INDEX IF NOT EXISTS idx_snapshot_date ON source_snapshots(snapshot_date);

-- Таблица версий датасетов для ML
CREATE TABLE IF NOT EXISTS dataset_versions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'preparing',  -- preparing, ready, training, archived
    total_samples INTEGER DEFAULT 0,
    size_mb FLOAT,
    base_version_id INTEGER REFERENCES dataset_versions(id),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dataset_status ON dataset_versions(status);
CREATE INDEX IF NOT EXISTS idx_base_version ON dataset_versions(base_version_id);

-- Таблица образцов датасетов
CREATE TABLE IF NOT EXISTS dataset_samples (
    id SERIAL PRIMARY KEY,
    version_id INTEGER REFERENCES dataset_versions(id) ON DELETE CASCADE,
    document_id TEXT,
    sample_data JSONB NOT NULL,  -- Форматированные данные для обучения
    sample_hash VARCHAR(64),  -- Хеш для дедупликации
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_version_id ON dataset_samples(version_id);
CREATE INDEX IF NOT EXISTS idx_sample_hash ON dataset_samples(sample_hash);
CREATE INDEX IF NOT EXISTS idx_document_id ON dataset_samples(document_id);

-- Таблица для отслеживания изменений документов
CREATE TABLE IF NOT EXISTS document_changes (
    id SERIAL PRIMARY KEY,
    document_id TEXT NOT NULL,
    change_type VARCHAR(50),  -- created, updated, deleted
    old_content_hash VARCHAR(64),
    new_content_hash VARCHAR(64),
    changed_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_document_changes ON document_changes(document_id, changed_at);
CREATE INDEX IF NOT EXISTS idx_change_type ON document_changes(change_type);

-- Функция для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Триггеры для автоматического обновления updated_at
CREATE TRIGGER update_data_sources_updated_at BEFORE UPDATE ON data_sources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_dataset_versions_updated_at BEFORE UPDATE ON dataset_versions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

