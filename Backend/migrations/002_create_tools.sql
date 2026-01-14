-- RABA Database Migration: Create tools table
-- Version: 002
-- Description: Tool repository for video generation strategies

CREATE TABLE IF NOT EXISTS tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Tool identification
    tool_id VARCHAR(100) UNIQUE NOT NULL,
    tool_name VARCHAR(255) NOT NULL,
    category VARCHAR(50) NOT NULL CHECK (category IN ('surreal_realism', 'high_octane_anime', 'stylized_3d')),
    
    -- Tool metadata
    description TEXT,
    capabilities JSONB,
    
    -- Prompt templates
    script_prompt_template TEXT,
    image_prompt_template TEXT,
    video_prompt_template TEXT,
    
    -- Configuration
    is_active BOOLEAN NOT NULL DEFAULT true,
    priority INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_tools_category ON tools(category);
CREATE INDEX IF NOT EXISTS idx_tools_is_active ON tools(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_tools_tool_id ON tools(tool_id);

-- Updated_at trigger
DROP TRIGGER IF EXISTS update_tools_updated_at ON tools;
CREATE TRIGGER update_tools_updated_at
    BEFORE UPDATE ON tools
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Seed initial tools
INSERT INTO tools (tool_id, tool_name, category, description, capabilities, is_active, priority)
VALUES 
    (
        'surreal_impossible_sims',
        'Impossible Simulations',
        'surreal_realism',
        'Visualize invisible forces and structures using flowing, liquid-glass aesthetics',
        '{"flow_visualization": true, "invisible_forces": true, "photorealistic_grounding": true}'::jsonb,
        true,
        100
    ),
    (
        'anime_concept_combat',
        'Concept Combat',
        'high_octane_anime',
        'Recreate topics as high-energy Sakuga-style philosophical battles',
        '{"philosophical_debates": true, "sakuga_style": true, "calligraphic_combat": true}'::jsonb,
        true,
        90
    ),
    (
        'stylized_data_dioramas',
        'Data Dioramas',
        'stylized_3d',
        'Transform statistics and data into physical miniature landscapes',
        '{"data_visualization": true, "miniature_style": true, "3d_rendering": true}'::jsonb,
        true,
        80
    )
ON CONFLICT (tool_id) DO NOTHING;

-- Comments
COMMENT ON TABLE tools IS 'Tool repository for video generation strategies';
COMMENT ON COLUMN tools.tool_id IS 'Unique identifier for the tool (used in code)';
COMMENT ON COLUMN tools.category IS 'Visual style category: surreal_realism, high_octane_anime, stylized_3d';
COMMENT ON COLUMN tools.priority IS 'Selection priority when multiple tools match (higher = preferred)';
