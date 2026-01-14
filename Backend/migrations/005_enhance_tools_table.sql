-- RABA Database Migration: Enhance tools table
-- Version: 005
-- Description: Add columns to support AI-enhanced tool creation and analytics

-- Add version tracking
ALTER TABLE tools ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1;

-- Add usage analytics
ALTER TABLE tools ADD COLUMN IF NOT EXISTS usage_count INTEGER DEFAULT 0;
ALTER TABLE tools ADD COLUMN IF NOT EXISTS success_rate FLOAT DEFAULT 0.0;

-- Add parameters schema for tool execution validation
ALTER TABLE tools ADD COLUMN IF NOT EXISTS parameters_schema JSONB;

-- Add original idea (for tools created via AI enhancement)
ALTER TABLE tools ADD COLUMN IF NOT EXISTS original_idea TEXT;

-- Add creator reference (nullable for seed tools)
ALTER TABLE tools ADD COLUMN IF NOT EXISTS created_by UUID;

-- Add improvement tracking (stores history of improvements)
ALTER TABLE tools ADD COLUMN IF NOT EXISTS improvement_history JSONB DEFAULT '[]'::jsonb;

-- Add last_improved_at timestamp
ALTER TABLE tools ADD COLUMN IF NOT EXISTS last_improved_at TIMESTAMPTZ;

-- Index for usage analytics queries
CREATE INDEX IF NOT EXISTS idx_tools_usage_count ON tools(usage_count DESC);
CREATE INDEX IF NOT EXISTS idx_tools_success_rate ON tools(success_rate DESC);

-- Function to increment usage count
CREATE OR REPLACE FUNCTION increment_tool_usage(p_tool_id VARCHAR)
RETURNS void AS $$
BEGIN
    UPDATE tools 
    SET usage_count = usage_count + 1,
        updated_at = NOW()
    WHERE tool_id = p_tool_id;
END;
$$ LANGUAGE plpgsql;

-- Function to update success rate
CREATE OR REPLACE FUNCTION update_tool_success_rate(p_tool_id VARCHAR, p_success BOOLEAN)
RETURNS void AS $$
DECLARE
    current_count INTEGER;
    current_rate FLOAT;
    new_rate FLOAT;
BEGIN
    SELECT usage_count, success_rate INTO current_count, current_rate
    FROM tools WHERE tool_id = p_tool_id;
    
    IF current_count > 0 THEN
        -- Calculate new weighted success rate
        IF p_success THEN
            new_rate := ((current_rate * (current_count - 1)) + 1.0) / current_count;
        ELSE
            new_rate := (current_rate * (current_count - 1)) / current_count;
        END IF;
        
        UPDATE tools 
        SET success_rate = new_rate,
            updated_at = NOW()
        WHERE tool_id = p_tool_id;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Update existing tools with default parameters_schema
UPDATE tools 
SET parameters_schema = '{
    "type": "object",
    "properties": {
        "tone": {
            "type": "string",
            "enum": ["serious", "humorous", "dramatic", "casual"],
            "default": "engaging"
        },
        "duration_seconds": {
            "type": "integer",
            "minimum": 8,
            "maximum": 25,
            "default": 18
        }
    }
}'::jsonb
WHERE parameters_schema IS NULL;

-- Comments
COMMENT ON COLUMN tools.version IS 'Tool revision number, incremented on each update';
COMMENT ON COLUMN tools.usage_count IS 'Number of times this tool has been used';
COMMENT ON COLUMN tools.success_rate IS 'Success rate of video generations using this tool (0.0-1.0)';
COMMENT ON COLUMN tools.parameters_schema IS 'JSON Schema for validating tool execution parameters';
COMMENT ON COLUMN tools.original_idea IS 'Original user idea if tool was created via AI enhancement';
COMMENT ON COLUMN tools.created_by IS 'UUID of user who created the tool (null for seed tools)';
COMMENT ON COLUMN tools.improvement_history IS 'Array of improvement records with timestamps and changes';
COMMENT ON COLUMN tools.last_improved_at IS 'Timestamp of last improvement/enhancement';
