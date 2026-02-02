#!/bin/bash

# Bulk update all tools to support Ingredients strategy
# This script updates tool templates to generate 3 separate images (Subject, Environment, Object)

curl -X 'POST' \
  'http://0.0.0.0:8000/api/v1/tools/prompts/bulk-update' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "tool_ids": [],
  "update_type": "all",
  "improvement_reason": "Veo 3.1 Ingredients Strategy: IMAGE templates must generate 3 SEPARATE images (Subject/Environment/Object) using {ingredient_type}, {ingredient_subject}, {ingredient_environment}, {ingredient_object} placeholders with conditional logic. Remove storyboard/composite language. Preserve {scene_description}, {style}, {user_topic}, {text_overlay_mode}, {image_negative_constraint}. Include technical sections: lighting, color, composition, resolution with concrete parameters (lens specs, GI angles, PBR, hex colors, Golden Spiral, 8K). Add 50-100 word Negative Constraints (no text/watermarks/artifacts). Min 150 words. SCRIPT templates: preserve {topic}, {tone}, {duration}, {user_topic}, {audio_mode}, {text_overlay_mode}. Include HOOK, pattern, interrupt, CTA. Require VO Text, Visual Action, Camera Metadata per scene. When audio_mode=silent: visual-only. When text_overlay_mode=no_text: forbid on-screen text. No bracketed metadata in visuals. Min 150 words. VIDEO templates: preserve {script}, {duration}, {image_reference}, {user_topic}, {audio_instruction}, {subtitle_instruction}. Add segment placeholders if missing. Remove timestamp SFX (use event-anchored). Include camera, angle, pacing, effects, audio, consistency keywords. Min 150 words. Keep tool_id, category, capabilities unchanged.",
  "use_ai_enhancement": true
}'
