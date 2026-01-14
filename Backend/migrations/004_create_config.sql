-- RABA Database Migration: Create config table
-- Version: 004
-- Description: Dynamic configuration storage

CREATE TABLE IF NOT EXISTS config (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Updated_at trigger
DROP TRIGGER IF EXISTS update_config_updated_at ON config;
CREATE TRIGGER update_config_updated_at
    BEFORE UPDATE ON config
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Seed default configuration
INSERT INTO config (key, value, description)
VALUES 
    (
        'video_generation',
        '{
            "default_duration_seconds": 18,
            "min_duration_seconds": 8,
            "max_duration_seconds": 25,
            "default_aspect_ratio": "9:16",
            "default_resolution": "1080p",
            "max_segment_duration": 8
        }'::jsonb,
        'Video generation default settings'
    ),
    (
        'hitl',
        '{
            "max_regeneration_attempts": 3,
            "default_mode": "auto",
            "gates": ["tool_selection", "research", "script", "images", "video"]
        }'::jsonb,
        'Human-in-the-loop configuration'
    ),
    (
        'cache_ttl',
        '{
            "research_seconds": 604800,
            "tools_seconds": 3600,
            "scripts_seconds": 86400
        }'::jsonb,
        'Cache time-to-live settings'
    ),
    (
        'models',
        '{
            "intent_tool_selector": "gemini-2.5-flash",
            "deep_research": "gemini-2.5-pro",
            "script_writer": "gemini-2.5-pro",
            "image_generator": "gemini-2.5-pro-image",
            "video_generator": "veo-3.1"
        }'::jsonb,
        'AI model configuration for each agent'
    )
ON CONFLICT (key) DO NOTHING;

-- Comments
COMMENT ON TABLE config IS 'Dynamic configuration key-value store';
COMMENT ON COLUMN config.key IS 'Configuration key (unique identifier)';
COMMENT ON COLUMN config.value IS 'Configuration value as JSON';
