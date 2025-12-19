-- Supabase 数据库表结构
-- 请在 Supabase Dashboard -> SQL Editor 中执行此脚本

-- 主记录表
CREATE TABLE IF NOT EXISTS property_records (
    id BIGSERIAL PRIMARY KEY,
    timestamp TEXT NOT NULL,
    available_units INTEGER NOT NULL,
    total_projects INTEGER DEFAULT 0,
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 楼盘详细记录表
CREATE TABLE IF NOT EXISTS property_details (
    id BIGSERIAL PRIMARY KEY,
    timestamp TEXT NOT NULL,
    property_name TEXT NOT NULL,
    available_units INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_property_name 
ON property_details(property_name, timestamp);

CREATE INDEX IF NOT EXISTS idx_property_records_timestamp 
ON property_records(timestamp);

CREATE INDEX IF NOT EXISTS idx_property_details_timestamp 
ON property_details(timestamp);

