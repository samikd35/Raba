# Raba Robustness Fix Strategy

This document outlines the critical issues identified in the current Raba video generation pipeline and the corresponding solutions to align with "Production-Ready" recommendations.

## 1. Prompt Sanitization & "Layered" Intent

### **Issue**
The current **Script Generato Agent** passes raw script metadata (including bracketed audio cues like `[Upbeat music]`, `[Sound of rain]`) directly into downstream image and video generation prompts.
*   **Impact**: Image generators confuse audio instructions with visual descriptions, leading to hallucinations or text artifacts in generated images.

### **Solution**
Implement a **Prompt Sanitizer** within the Script Generator and enforce it at the tool template layer.
*   **Action**: Create a `clean_visual_prompt` utility that strictly strips all text within brackets `[...]` from the description fields before passing them to the Image/Video agents.
*   **Action**: Update the Script Agent's output structure to separate "Visual Translation" (what we see) from "Audio/Fact" (what we hear).
*   **Tool Integration**: Update `script_prompt_template` guidance (via Tool Enhancer system prompts) to explicitly prohibit bracketed audio/SFX metadata in visual directives and to produce three distinct fields per scene: VO Text, Visual Action, Camera Metadata. Add validation to reject templates missing this separation.

---

## 2. Visual Validation Loop

### **Issue**
There is no feedback loop between image generation and video assembly. The system assumes generated images are correct.
*   **Impact**: If the Image Generator creates "fuzzy blue balls" for a "mitochondria" request, the Video Generator will animate those incorrect assets, resulting in a low-quality final video.

### **Solution**
Implement a **Visual Validation Agent** using a Vision-Language Model (VLM) like Gemini 3 Flash.
*   **Workflow**: `Script Segment` + `Generated Image` -> `VLM Critique`.
*   **Logic**: The VLM asks, "Does this image accurately represent [Segment Concept]?".
*   **Action**: If the VLM returns `REGENERATE`, the system triggers a retry with the VLM's specific critique injected into the new prompt constraints.
*   **Tool Integration**: Define a lightweight, per-tool "validation contract" (e.g., critical entities/attributes the image must depict) emitted alongside the tool’s templates. This informs the VLM prompt and regeneration constraints without hardcoding per-agent logic.

---

## 3. "Ingredients" vs. Single Reference

### **Issue**
The system currently generates a single "Master Style Frame" or sequential scene images.
*   **Impact**: When passed to Veo 3.1, a single abstract or complex image effectively "poisons" the style of the entire video, causing it to over-index on that one image's specific look rather than the general subject matter.

### **Solution**
Adopt the **"Ingredients" Strategy** for Veo 3.1 reference images. Instead of scene flow, we generate 3 distinct "Ingredient" assets:
1.  **Subject**: The consistent character/host (or main actor).
2.  **Environment**: A neutral, high-quality background (e.g., clean medical lab, sterile white void).
3.  **Object/Concept**: The specific scientific diagram or element (e.g., the cell, the molecule).

**Benefit**: Veo 3.1 can composite these independent elements (Subject + Object + Environment) much more effectively than it can "un-bake" a single complex scene image.
*   **Tool Integration**: Extend `image_prompt_template` requirements so tools output a storyboard-style composite that includes explicit slots for Subject, Environment, and Object/Concept, plus consistency guidance. Add placeholders (e.g., `{ingredient_subject}`, `{ingredient_environment}`, `{ingredient_object}`) or reuse existing storyboard placeholders with clear mapping.

---

## 4. Scientific "Cinematographer" Prompting

### **Issue**
Current prompts are often generic or "storyboard" style, which leads to "fuzzy" or "artistic" interpretations of scientific facts.

### **Solution**
Enforce a system-wide **Technical Prompt Template** for Nano Banana Pro and Veo.
*   **Formula**: `[Subject]` + `[Action]` + `[Composition]` + `[Style]` + `[Constraint]`
*   **Example**: `[A red blood cell]` + `[pulsating slowly]` + `[Extreme Close-up / Microscopic]` + `[Scientific Infographic style, 4K resolution, sharp focus]` + `[No text overlays, clean background]`.
*   **Tool Integration**: Encode this formula directly into `script_prompt_template`, `image_prompt_template`, and `video_prompt_template` via the Tool Enhancer. The Tool Validator must enforce presence of technical sections (camera/lens, lighting, composition, resolution, negative constraints) and user-mode awareness (audio/text overlay modes).

---

## Summary of Architecture Changes

| Feature | Current State | Target State |
| :--- | :--- | :--- |
| **Flow** | Research -> Script -> Asset -> Video | Research -> Script -> **Clean** -> **Ingredients** -> **VLM Check** -> Video |
| **References** | Single Master Frame / Scenes | **3 "Ingredients" (Subject, Env, Object)** |
| **Sanitization** | Raw metadata passed | **Stripped audio tags / Clean Visuals** |
| **Validation** | None (Fire & Forget) | **VLM Feedback Loop** |
| **Prompt Generation** | Ad-hoc per agent | **Centralized via Tool Templates + Validation** |

---

## 5. Tool Creation/Enhancement Integration (CRITICAL)

RABA’s tool creation/enhancement system owns prompt template generation. All robustness fixes must be enforced at this layer so every agent benefits consistently.

### Objectives
- Centralize prompt quality rules within `TOOL_ENHANCEMENT_SYSTEM_PROMPT` and `TOOL_IMPROVEMENT_SYSTEM_PROMPT`.
- Validate templates with `app/services/template_validation.py` so bad templates never reach runtime.
- Enable bulk regeneration of existing tools after rules change to propagate improvements.

### Required Changes
- Tool Enhancer (Backend/app/services/tool_enhancer.py)
  - Update `TOOL_ENHANCEMENT_SYSTEM_PROMPT` to explicitly require:
    - Layered intent: separate VO Text, Visual Action, Camera Metadata per scene; forbid bracketed audio cues in visuals; enforce audio/text-overlay mode awareness.
    - Ingredients-first references: generate Subject, Environment, Object/Concept in storyboard-style composites and/or explicit placeholders.
    - Scientific cinematography: camera/lens, lighting, composition, resolution, negative constraints with technical, not poetic, parameters.
    - VLM validation contract: emit a concise, per-tool checklist of must-appear entities/attributes to drive the validation loop.
  - Update `TOOL_IMPROVEMENT_SYSTEM_PROMPT` to align with the above and support bulk upgrades.

- Template Validator (Backend/app/services/template_validation.py)
  - Enforce presence of technical sections (lighting, color, composition, resolution) and negative constraints for image templates.
  - Enforce script template keywords (HOOK, pattern, interrupt, CTA) and scene field separation.
  - Optionally add checks for Ingredients placeholders or storyboard placeholders to guarantee multi-entity composites.

- Tool Templates (DB `tools` table)
  - Ensure `script_prompt_template`, `image_prompt_template`, `video_prompt_template` include the new placeholders and constraints.
  - For `image_prompt_template`, require either explicit Ingredients placeholders or storyboard composition that maps to Subject/Env/Object.

### Rollout Plan
1. Update Enhancer + Validator prompts/rules.
2. Run Bulk Improve on all existing tools to regenerate templates with new constraints.
3. Smoke-test generation with 3–5 representative tools across categories (realistic, anime, animation).
4. Monitor validation error rates; adjust validator messaging for developer clarity.

---

## 6. Workflow & State Integration

Ensure LangGraph workflows use tool-generated templates and surface new artifacts for persistence and HITL gates.

- Script Writer Node
  - Apply `clean_visual_prompt` before passing scene data to downstream agents.
  - Persist separated fields (VO, Visual Action, Camera Metadata) in state.

- Image Generator Node
  - Build prompts strictly from the selected tool’s `image_prompt_template` with Ingredients/storyboard placeholders populated.
  - Save generated Subject/Environment/Object references separately in state (`generated_images`, `image_metadata`).

- Visual Validation Node
  - Use Gemini VLM with the per-tool validation contract and current scene/ingredients.
  - On `REGENERATE`, inject VLM critique into regeneration constraints; respect retry caps and HITL gates.

- Video Generator Node
  - Pass ingredients and validated prompts to Veo 3.1; maintain consistency constraints from tools.

---

## 7. Documentation & API Updates

- Documentation
  - Update `Backend/Documentations/nano_prompt_guide.md`, `veo_prompting_guide.md`, and `veo_doc.md` to reflect Ingredients-first references, sanitization rules, and validator expectations.
  - Update `Backend/Documentations/gemini_doc.md` with VLM validation prompt patterns and expected outputs.
  - Sync database schema notes in `Backend/Documentations/tables.sql` if new template fields or flags are added.

- API
  - Document the Bulk Improve endpoint/flow in `Backend/Documentations/API_Docs/` and ensure response payloads include validator errors when templates fail.

---

## 8. Acceptance Criteria

- Tool templates generated after bulk improvement pass Template Validator with zero errors.
- Scripts no longer leak bracketed audio cues into visual prompts; visuals remain clean when `text_overlay_mode=no_text`.
- Image generation returns coherent Subject/Environment/Object assets; Veo composites show improved consistency.
- Visual Validation loop prevents off-target images from reaching video assembly; measurable decrease in regeneration loops after first pass.
- No regressions in existing LangGraph state structure and node contracts; HITL gates preserved.
