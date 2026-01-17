-- Add user-selected tool column to workflows for persisted preference

ALTER TABLE public.workflows
ADD COLUMN IF NOT EXISTS user_selected_tool_id TEXT;

COMMENT ON COLUMN public.workflows.user_selected_tool_id IS 'Optional tool_id chosen by the user at input time. If present, agents must use this tool.';

