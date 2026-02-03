-- Add VB profile fields for name/email/main_expertise/short_intro
ALTER TABLE public.venture_builders
    ADD COLUMN IF NOT EXISTS name TEXT,
    ADD COLUMN IF NOT EXISTS main_expertise TEXT,
    ADD COLUMN IF NOT EXISTS short_intro TEXT;

-- Update view to include the new fields
DROP VIEW IF EXISTS public.vb_with_expertise;
CREATE OR REPLACE VIEW public.vb_with_expertise AS
SELECT
    vb.id,
    vb.user_id,
    vb.contact_email,
    vb.name,
    vb.main_expertise,
    vb.short_intro,
    vb.profile_picture_url,
    vb.biography,
    vb.linkedin_url,
    vb.credit_price_per_hour,
    vb.status,
    vb.work_experience,
    vb.created_at,
    vb.updated_at,
    COALESCE(
        json_agg(
            json_build_object(
                'id', exp.id,
                'name', exp.name,
                'description', exp.description
            ) ORDER BY exp.display_order
        ) FILTER (WHERE exp.id IS NOT NULL),
        '[]'::json
    ) as areas_of_expertise
FROM public.venture_builders vb
LEFT JOIN public.vb_expertise_mapping vem ON vb.id = vem.venture_builder_id
LEFT JOIN public.vb_areas_of_expertise exp ON vem.expertise_id = exp.id AND exp.is_active = true
GROUP BY vb.id;
