-- Migration: Add pitch_deck_data column to vmp_projects
-- This column stores all pitch deck generations with versioning

-- Add the pitch_deck_data JSONB column
ALTER TABLE public.vmp_projects 
ADD COLUMN IF NOT EXISTS pitch_deck_data jsonb DEFAULT '{}'::jsonb;

-- Add pitch_deck_status column for tracking generation status
ALTER TABLE public.vmp_projects 
ADD COLUMN IF NOT EXISTS pitch_deck_status character varying 
DEFAULT 'not_started'::character varying 
CHECK (pitch_deck_status::text = ANY (ARRAY[
    'not_started'::character varying, 
    'processing'::character varying, 
    'completed'::character varying, 
    'failed'::character varying
]::text[]));

-- Comment explaining the structure
COMMENT ON COLUMN public.vmp_projects.pitch_deck_data IS '
Stores pitch deck generations with versioning. Structure:
{
  "current_version": 1,
  "versions": [
    {
      "version": 1,
      "deck_purpose": "FUNDRAISING|PARTNER_SALES|DEMO",
      "stage": "IDEATION|PRE_SEED|SEED|GROWTH",
      "category": "PLATFORM_SAAS|CPG|INFRA_PROJECT|OTHER",
      "slides": [
        {
          "slide_type": "Problem|Solution|...",
          "slide_title": "...",
          "slide_bullets": ["...", "..."],
          "description": "... [P1] ... [W1] ...",
          "citations_used": ["P1", "W1"],
          "placeholders": [{"field": "...", "prompt": "..."}],
          "warnings": []
        }
      ],
      "citations": [
        {"id": "P1", "type": "project", "artifact_ref": "...", "chunk_ref": "...", "snippet": "..."},
        {"id": "W1", "type": "web", "url": "...", "domain": "...", "title": "...", "snippet": "...", "fetched_at": "..."}
      ],
      "warnings": [],
      "user_inputs": {},
      "run_trace": {
        "retrieval_queries": [],
        "web_queries": [],
        "latency_ms": 0,
        "tokens_used": 0
      },
      "status": "completed|failed",
      "error_message": null,
      "created_at": "ISO timestamp",
      "created_by": "user_id"
    }
  ]
}
';
