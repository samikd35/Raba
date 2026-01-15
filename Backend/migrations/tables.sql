-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.agents_state (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  video_id uuid,
  agent_name text NOT NULL,
  model text,
  input_tokens integer DEFAULT 0,
  output_tokens integer DEFAULT 0,
  api_calls integer DEFAULT 1,
  estimated_cost_usd numeric DEFAULT 0,
  output_json jsonb,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT agents_state_pkey PRIMARY KEY (id),
  CONSTRAINT agents_state_video_id_fkey FOREIGN KEY (video_id) REFERENCES public.videos(id)
);
CREATE TABLE public.character_aliases (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  character_id uuid,
  alias text NOT NULL,
  alias_type text CHECK (alias_type = ANY (ARRAY['nickname'::text, 'abbreviation'::text, 'alternative_name'::text])),
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT character_aliases_pkey PRIMARY KEY (id),
  CONSTRAINT character_aliases_character_id_fkey FOREIGN KEY (character_id) REFERENCES public.characters(id)
);
CREATE TABLE public.character_pillar_associations (
  character_id uuid NOT NULL,
  pillar_name text NOT NULL,
  usage_count integer DEFAULT 0,
  avg_performance double precision,
  CONSTRAINT character_pillar_associations_pkey PRIMARY KEY (character_id, pillar_name),
  CONSTRAINT character_pillar_associations_character_id_fkey FOREIGN KEY (character_id) REFERENCES public.characters(id),
  CONSTRAINT character_pillar_associations_pillar_name_fkey FOREIGN KEY (pillar_name) REFERENCES public.content_pillars(name)
);
CREATE TABLE public.characters (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  name text NOT NULL UNIQUE,
  description text,
  physical_traits jsonb,
  reference_image_url text,
  embedding USER-DEFINED,
  created_at timestamp with time zone DEFAULT now(),
  is_llm_generated boolean DEFAULT false,
  generation_confidence double precision,
  generated_at timestamp with time zone,
  generation_context jsonb,
  reference_source text CHECK (reference_source = ANY (ARRAY['user_upload'::text, 'search'::text, 'generated'::text, 'none'::text])),
  CONSTRAINT characters_pkey PRIMARY KEY (id)
);
CREATE TABLE public.config (
  key text NOT NULL,
  value jsonb NOT NULL,
  description text,
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT config_pkey PRIMARY KEY (key)
);
CREATE TABLE public.content_pillars (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  name text NOT NULL UNIQUE,
  category text CHECK (category = ANY (ARRAY['real-time'::text, 'evergreen'::text])),
  target_audience ARRAY,
  narrative_engine text,
  emotional_trigger text,
  priority_score double precision DEFAULT 1.0,
  usage_count integer DEFAULT 0,
  avg_engagement double precision,
  description text,
  keywords ARRAY,
  example_topics ARRAY,
  is_active boolean DEFAULT true,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT content_pillars_pkey PRIMARY KEY (id)
);
CREATE TABLE public.evergreen_ideas (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  title text NOT NULL,
  script_outline text,
  content_pillar text,
  tags ARRAY,
  last_used_at timestamp with time zone,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT evergreen_ideas_pkey PRIMARY KEY (id)
);
CREATE TABLE public.human_approvals (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  video_id uuid,
  gate_name text NOT NULL,
  approved boolean NOT NULL,
  feedback text,
  approved_by text,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT human_approvals_pkey PRIMARY KEY (id),
  CONSTRAINT human_approvals_video_id_fkey FOREIGN KEY (video_id) REFERENCES public.videos(id)
);
CREATE TABLE public.image_assets (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  video_id uuid,
  storyboard_url text,
  storyboard_storage_url text,
  frames jsonb DEFAULT '[]'::jsonb,
  frame_count integer DEFAULT 0,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT image_assets_pkey PRIMARY KEY (id),
  CONSTRAINT image_assets_video_id_fkey FOREIGN KEY (video_id) REFERENCES public.videos(id)
);
CREATE TABLE public.knowledge_base (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  content text NOT NULL,
  source text,
  category text,
  embedding USER-DEFINED,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT knowledge_base_pkey PRIMARY KEY (id)
);
CREATE TABLE public.videos (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  topic text,
  mode text CHECK (mode = ANY (ARRAY['real-time'::text, 'evergreen'::text])),
  status text DEFAULT 'pending'::text CHECK (status = ANY (ARRAY['pending'::text, 'in_progress'::text, 'completed'::text, 'failed'::text])),
  video_url text,
  error text,
  human_approved boolean DEFAULT false,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  primary_pillar text,
  secondary_pillars ARRAY,
  CONSTRAINT videos_pkey PRIMARY KEY (id)
);