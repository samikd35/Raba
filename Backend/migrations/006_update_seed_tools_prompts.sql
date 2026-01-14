-- RABA Database Migration: Update seed tools with prompt templates
-- Version: 006
-- Description: Fill in prompt templates for initial seed tools

-- Update Surreal Realism - "Impossible Simulations"
UPDATE tools 
SET 
    script_prompt_template = 'Create a {duration}-second viral YouTube Shorts script about: {topic}

Tone: {tone}
Visual Style: Surreal Realism - Impossible Simulations

REQUIREMENTS:
- Hook in first 2 seconds with an impossible visual concept
- Show invisible forces (gravity, magnetism, air pressure) as visible flowing substances
- Use liquid-glass aesthetics with photorealistic grounding
- Create "what if you could SEE..." moments
- Pattern interrupt every 3-5 seconds with mind-bending visuals
- End with a satisfying resolution that reveals the hidden beauty of physics

VIRAL SIGNAL: "Information without Boredom" - Make the invisible visible in stunning ways.',

    image_prompt_template = 'Generate a keyframe image for: {scene_description}

Style: Surreal Realism - Impossible Simulations
Visual Approach: {style}

REQUIREMENTS:
- Photorealistic base with impossible/surreal elements
- Visualize invisible forces as flowing, liquid-glass substances
- High detail and clarity suitable for video generation
- Dramatic lighting that emphasizes the surreal elements
- Color palette: Deep blues, ethereal whites, hints of impossible colors
- Show the beauty hidden in everyday physics',

    video_prompt_template = 'Create a {duration}-second video segment based on:

Script: {script}

Style: Surreal Realism - Impossible Simulations
Category: surreal_realism

VISUAL DIRECTION:
- Smooth, flowing camera movements
- Liquid-glass visual effects for invisible forces
- Photorealistic environments with surreal overlays
- Maintain visual consistency across all frames
- Audio: Ambient, ethereal soundscape with subtle wonder

PACING: Match script timing with visual reveals'

WHERE tool_id = 'surreal_impossible_sims';


-- Update High-Octane Anime - "Concept Combat"
UPDATE tools 
SET 
    script_prompt_template = 'Create a {duration}-second viral YouTube Shorts script about: {topic}

Tone: {tone}
Visual Style: High-Octane Anime - Concept Combat

REQUIREMENTS:
- Open with a dramatic confrontation setup
- Personify abstract concepts as anime warriors/entities
- Use sakuga-style animation language (speed lines, impact frames)
- Include calligraphic visual effects for emphasis
- Build tension through concept vs concept narrative
- Climax with an epic clash that illuminates the topic
- Resolution that leaves viewers thinking

VIRAL SIGNAL: "Zen-Action" - Transform ideas into epic battles.',

    image_prompt_template = 'Generate a keyframe image for: {scene_description}

Style: High-Octane Anime - Concept Combat
Visual Approach: {style}

REQUIREMENTS:
- Sakuga-style anime aesthetic with dynamic poses
- Calligraphic ink-splash effects
- Personified concepts as distinct anime characters
- Dramatic lighting with high contrast
- Action lines and impact emphasis
- Color palette: Bold primaries with ink-black accents
- Cinematic composition with clear focal point',

    video_prompt_template = 'Create a {duration}-second video segment based on:

Script: {script}

Style: High-Octane Anime - Concept Combat
Category: high_octane_anime

VISUAL DIRECTION:
- Dynamic camera movements (zooms, pans, impact shots)
- Sakuga-style animation with fluid motion
- Calligraphic effects on key moments
- Speed lines and impact frames
- Maintain character consistency
- Audio: Epic orchestral with dramatic beats

PACING: Fast cuts during action, slower for dramatic moments'

WHERE tool_id = 'anime_concept_combat';


-- Update Stylized 3D - "Data Dioramas"
UPDATE tools 
SET 
    script_prompt_template = 'Create a {duration}-second viral YouTube Shorts script about: {topic}

Tone: {tone}
Visual Style: Stylized 3D - Data Dioramas

REQUIREMENTS:
- Open with a bird''s-eye view of a miniature world
- Transform data/statistics into physical landscapes
- Use tilt-shift aesthetic for miniature effect
- Each data point becomes a tangible object or structure
- Guide viewer through the data story spatially
- Reveal surprising insights through visual comparison
- End with a zoom-out showing the full picture

VIRAL SIGNAL: "Abstract made Tangible" - Turn numbers into worlds.',

    image_prompt_template = 'Generate a keyframe image for: {scene_description}

Style: Stylized 3D - Data Dioramas
Visual Approach: {style}

REQUIREMENTS:
- Miniature diorama aesthetic with tilt-shift blur
- Data visualized as physical 3D objects
- Clean, stylized rendering (not photorealistic)
- Warm, inviting color palette
- Clear visual hierarchy showing data relationships
- Soft shadows and ambient occlusion
- Isometric or slight top-down perspective',

    video_prompt_template = 'Create a {duration}-second video segment based on:

Script: {script}

Style: Stylized 3D - Data Dioramas
Category: stylized_3d

VISUAL DIRECTION:
- Smooth fly-through and orbit camera movements
- Tilt-shift depth of field effect
- Stylized 3D rendering with soft lighting
- Data elements animate to show changes
- Maintain miniature world consistency
- Audio: Gentle, curious music with data-driven sound design

PACING: Slow, contemplative reveals with clear data moments'

WHERE tool_id = 'stylized_data_dioramas';


-- Add comments
COMMENT ON COLUMN tools.script_prompt_template IS 'Template for script generation - uses {topic}, {tone}, {duration} placeholders';
COMMENT ON COLUMN tools.image_prompt_template IS 'Template for image generation - uses {scene_description}, {style} placeholders';
COMMENT ON COLUMN tools.video_prompt_template IS 'Template for video generation - uses {script}, {duration} placeholders';
