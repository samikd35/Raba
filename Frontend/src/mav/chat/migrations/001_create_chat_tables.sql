-- Migration: Create Project Chat Tables
-- Description: Tables for threads, messages, and thread memory for Project Chat feature
-- Created: 2024-12-23

-- ============================================================================
-- TABLE: project_chat_threads
-- Description: Stores chat threads linked to VMP projects
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.project_chat_threads (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    project_id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    user_id uuid NOT NULL,
    title text,
    status text NOT NULL DEFAULT 'active'::text,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    last_message_at timestamp with time zone,
    metadata jsonb DEFAULT '{}'::jsonb,
    CONSTRAINT project_chat_threads_pkey PRIMARY KEY (id),
    CONSTRAINT project_chat_threads_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.vmp_projects(id) ON DELETE CASCADE,
    CONSTRAINT project_chat_threads_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE,
    CONSTRAINT project_chat_threads_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.user_profiles(id) ON DELETE CASCADE,
    CONSTRAINT project_chat_threads_status_check CHECK (status = ANY (ARRAY['active'::text, 'archived'::text, 'deleted'::text]))
);

-- Indexes for project_chat_threads
CREATE INDEX IF NOT EXISTS idx_chat_threads_project ON public.project_chat_threads(project_id, tenant_id);
CREATE INDEX IF NOT EXISTS idx_chat_threads_user ON public.project_chat_threads(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_threads_status ON public.project_chat_threads(status) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_chat_threads_last_message ON public.project_chat_threads(last_message_at DESC NULLS LAST);

-- ============================================================================
-- TABLE: project_chat_messages
-- Description: Stores all messages in threads (user, assistant, tool, system)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.project_chat_messages (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    thread_id uuid NOT NULL,
    role text NOT NULL,
    content text NOT NULL,
    citations jsonb DEFAULT '[]'::jsonb,
    tool_trace jsonb,
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT project_chat_messages_pkey PRIMARY KEY (id),
    CONSTRAINT project_chat_messages_thread_id_fkey FOREIGN KEY (thread_id) REFERENCES public.project_chat_threads(id) ON DELETE CASCADE,
    CONSTRAINT project_chat_messages_role_check CHECK (role = ANY (ARRAY['user'::text, 'assistant'::text, 'tool'::text, 'system'::text]))
);

-- Indexes for project_chat_messages
CREATE INDEX IF NOT EXISTS idx_chat_messages_thread ON public.project_chat_messages(thread_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_messages_role ON public.project_chat_messages(thread_id, role);

-- ============================================================================
-- TABLE: project_chat_thread_memory
-- Description: Stores thread memory for continuity (summary, pinned facts, open loops)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.project_chat_thread_memory (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    thread_id uuid NOT NULL UNIQUE,
    running_summary text,
    pinned_facts jsonb DEFAULT '[]'::jsonb,
    open_loops jsonb DEFAULT '[]'::jsonb,
    last_context_refs jsonb DEFAULT '{}'::jsonb,
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT project_chat_thread_memory_pkey PRIMARY KEY (id),
    CONSTRAINT project_chat_thread_memory_thread_id_fkey FOREIGN KEY (thread_id) REFERENCES public.project_chat_threads(id) ON DELETE CASCADE
);

-- Index for thread memory
CREATE INDEX IF NOT EXISTS idx_chat_memory_thread ON public.project_chat_thread_memory(thread_id);

-- ============================================================================
-- FUNCTION: Update thread's last_message_at and updated_at on new message
-- ============================================================================
CREATE OR REPLACE FUNCTION update_thread_on_message()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE public.project_chat_threads
    SET 
        last_message_at = NEW.created_at,
        updated_at = now()
    WHERE id = NEW.thread_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update thread timestamps on new message
DROP TRIGGER IF EXISTS trigger_update_thread_on_message ON public.project_chat_messages;
CREATE TRIGGER trigger_update_thread_on_message
    AFTER INSERT ON public.project_chat_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_thread_on_message();

-- ============================================================================
-- FUNCTION: Initialize thread memory when thread is created
-- ============================================================================
CREATE OR REPLACE FUNCTION initialize_thread_memory()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.project_chat_thread_memory (thread_id)
    VALUES (NEW.id);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-create thread memory on thread creation
DROP TRIGGER IF EXISTS trigger_initialize_thread_memory ON public.project_chat_threads;
CREATE TRIGGER trigger_initialize_thread_memory
    AFTER INSERT ON public.project_chat_threads
    FOR EACH ROW
    EXECUTE FUNCTION initialize_thread_memory();

-- ============================================================================
-- FUNCTION: Vector similarity search for project chunks
-- Description: Search project chunks filtered by project (doc_id)
-- Note: Uses 'chunks' table with 'doc_id' column (project_id reference)
-- ============================================================================
CREATE OR REPLACE FUNCTION match_project_chunks(
    query_embedding vector(1536),
    p_project_id uuid,
    p_tenant_id uuid,  -- Kept for API compatibility, not used in query
    match_count int DEFAULT 10,
    match_threshold float DEFAULT 0.5
)
RETURNS TABLE (
    id uuid,
    content text,
    chunk_index int,
    section text,
    source_type text,
    metadata jsonb,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.content,
        c.chunk_index,
        NULL::text as section,  -- chunks table doesn't have section column
        (c.metadata->>'source_type')::text as source_type,
        c.metadata,
        1 - (c.embedding <=> query_embedding) as similarity
    FROM public.chunks c
    WHERE 
        c.doc_id = p_project_id
        AND 1 - (c.embedding <=> query_embedding) > match_threshold
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================

-- Enable RLS on all chat tables
ALTER TABLE public.project_chat_threads ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.project_chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.project_chat_thread_memory ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only access threads in their tenant
CREATE POLICY "Users can access own tenant threads" ON public.project_chat_threads
    FOR ALL
    USING (
        tenant_id IN (
            SELECT tm.tenant_id 
            FROM public.tenant_memberships tm 
            WHERE tm.user_id = auth.uid() AND tm.is_active = true
        )
    );

-- Policy: Users can only access messages in threads they can access
CREATE POLICY "Users can access messages in accessible threads" ON public.project_chat_messages
    FOR ALL
    USING (
        thread_id IN (
            SELECT t.id 
            FROM public.project_chat_threads t
            WHERE t.tenant_id IN (
                SELECT tm.tenant_id 
                FROM public.tenant_memberships tm 
                WHERE tm.user_id = auth.uid() AND tm.is_active = true
            )
        )
    );

-- Policy: Users can only access memory for threads they can access
CREATE POLICY "Users can access memory for accessible threads" ON public.project_chat_thread_memory
    FOR ALL
    USING (
        thread_id IN (
            SELECT t.id 
            FROM public.project_chat_threads t
            WHERE t.tenant_id IN (
                SELECT tm.tenant_id 
                FROM public.tenant_memberships tm 
                WHERE tm.user_id = auth.uid() AND tm.is_active = true
            )
        )
    );

-- ============================================================================
-- GRANTS for service role (bypasses RLS)
-- ============================================================================
GRANT ALL ON public.project_chat_threads TO service_role;
GRANT ALL ON public.project_chat_messages TO service_role;
GRANT ALL ON public.project_chat_thread_memory TO service_role;

-- Grant execute on functions
GRANT EXECUTE ON FUNCTION match_project_chunks TO service_role;
GRANT EXECUTE ON FUNCTION match_project_chunks TO authenticated;
