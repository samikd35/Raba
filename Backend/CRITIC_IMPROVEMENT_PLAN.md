# RABA Improvement Plan (Chief Critic Analysis)

Based on `sys_imp_guide.md`. This plan maps the critic’s recommendations to RABA’s pipeline: **Intent/Tool Selector → Deep Research → Script → Visual Logic Validator → Global Style Anchor → [Character Reference] → Image Generator (Nano Banana Pro) → Video Generator (Veo 3.1) → Trim → [Overlay] → Compositor → Output**, and to **tool templates** (`image_prompt_template`, `video_prompt_template`). **Audio:** we use **Veo 3.1’s native audio only** (no ElevenLabs, Udio, or other 3rd-party voiceover)—dialogue, SFX, ambient, and music are generated with the video for lip-sync and acoustic physics.

---

## Executive Summary

| # | Critic Issue | Root in RABA | Fix (High Level) |
|---|--------------|--------------|------------------|
| 1 | **Lazy Extension** – same prompt for all segments | Template path passes full `{script}` to every segment; fallback is segment-aware | Segment-specific `{segment_script}`, `{segment_action}`, `{previous_segment_state}`; Segment Splitter |
| 2 | **Optical Physics** – Anamorphic + Tilt-Shift mixed | Tool Enhancer uses generic “35mm Anamorphic”; no category lens rules | Optical presets per category; never Anamorphic in `stylized_3d` |
| 3 | **Audio Sync Hallucination** – “Place SFX at 3.2s, 7.5s” | Tool Enhancer injects SFX timestamps; Veo ignores them | **Veo 3.1 Native Audio only:** Optimal Audio Block (Dialogue, SFX, Ambient, Music), Action Anchor, 7s rule (≤15 words/segment), Master Voice Reference, no-subtitles guardrail; remove timestamp-based SFX |
| 4 | **Scene–Segment Mismatch / Ghost Time** – 8 scenes, 5 segments, 32s vs 36s | Segment planning is duration-only; trim only does edge jitter | Align segment math where possible; trim to `duration_seconds` when video is longer |
| 5 | **No Segment Splitter / Technical Editor** | Video Generator does planning + prompt build; no explicit segment context blocks | Add Segment Splitter (in Video Generator or helper); produce anchor/goal state, technical delta |
| 6 | **Anchor Image** – one style frame for every segment | We pass ref images only to initial segment; Veo extend has no image input | **One Master Style Frame only** (no per-scene images); ref for initial segment; for extensions, text continuity + `video=prev` |
| 7 | **Tool templates** – single `{script}` | `video_prompt_template` has `{script}`, `{duration}` only | Add `{segment_index}`, `{total_segments}`, `{segment_action}`, `{previous_segment_state}` |
| 8 | **Last-frame as image_input for Segment N+1** | Veo `extend_video` takes `video=prev`, not image | Keep `extend_video(video=prev)`; improve prompt content (segment-specific + continuity) |

---

## 1. Lazy Extension (Segment-Specific Prompting)

### Problem

- Segments 0–4 get the same prompt → Veo extends “Scene 1” for 36s then drifts.
- In RABA: when `video_prompt_template` is used, `_format_script_for_template(script_output)` gives the **full** script to every segment. The fallback `build_video_prompt` / `build_extension_prompt` already filters `relevant_scenes` by `segment_info.start_time`/`end_time`.

### Changes

1. **Segment Splitter (new helper or inside Video Generator)**  
   - Inputs: `script_output`, `segment_plans` from `plan_video_segments(duration_seconds)`.
   - For each segment, output:
     - `temporal_window`: (start_time, end_time)
     - `segment_script` / `segment_action`: only dialogue and visuals in that window (reuse `relevant_scenes` logic or Technical Editor LLM)
     - `anchor_state`: for segment 0, `"Initial state"`; for i>0, `goal_state` of segment i-1
     - `goal_state`: end state of this segment (from last relevant scene or 1-line summary)
   - Optional: `technical_delta` (camera move unique to this segment).

2. **Video Generator – template rendering**  
   - For **initial** and **each extension**, pass:
     - `segment_index`, `total_segments`
     - `segment_script` or `segment_action` (slice for this segment)
     - `previous_segment_state`
   - Prefer segment-specific content over full `{script}` when new placeholders exist.

3. **Tool / DB**  
   - Add optional placeholders to `video_prompt_template`:  
     `{segment_index}`, `{total_segments}`, `{segment_script}` or `{segment_action}`, `{previous_segment_state}`.
   - Backward compatible: if missing, keep `{script}` and `segment_info`.

4. **Files**

   - `app/agents/video_generator.py`: Segment Splitter logic, render context for templates and fallback.
   - `app/services/prompt_builder.py`: Support new placeholders (optional).
   - Migration or tool update: extend `video_prompt_template` schema; document in `03_TOOLS.md`.

---

## 2. Optical Physics (Anamorphic vs Tilt-Shift)

### Problem

- “35mm Anamorphic… to simulate a tilt-shift miniature effect” mixes two optics → blurry, inconsistent look.
- In RABA: `tool_enhancer.py` uses generic “35mm Anamorphic” in image and “35mm anamorphic” in video. Seed tools (e.g. `stylized_3d`) use tilt-shift correctly, but enhancer can overwrite.

### Optical Presets (from Critic)

| Category | Lens | Notes |
|----------|------|-------|
| **stylized_3d** | **Tilt-Shift** (35mm/50mm) | Never Anamorphic. Miniature/diorama. |
| **surreal_realism** | **Wide-Angle Anamorphic** (14–24mm) | Epic, widescreen. |
| **high_octane_anime** | **Dynamic Long Lens** (85–200mm) | Compression, action. |

### Changes

1. **Global Style Anchor**  
   - When setting `camera` (and any lens-like field), enforce the category’s optical preset. For `stylized_3d`, never output “Anamorphic”.

2. **Tool Enhancer**  
   - When generating/improving `image_prompt_template` or `video_prompt_template`, **inject the category-specific lens** from a preset map. Remove generic “35mm Anamorphic” for `stylized_3d`.

3. **Image Generator**  
   - If lens comes from `global_style_anchor` or tool, ensure `stylized_3d` only gets tilt-shift wording (e.g. “tilt-shift”, “35mm/50mm”, “miniature dof”).

4. **Seed / tool audit**  
   - Confirm `stylized_3d` tools never mention Anamorphic. Migration 006 is already tilt-shift; any new or enhanced tools must follow presets.

5. **Files**

   - `app/agents/global_style_anchor.py`: preset lookup and override for `camera`.
   - `app/services/tool_enhancer.py`: category → lens in image/video templates.
   - `app/agents/image_generator.py`: no Anamorphic for `stylized_3d` when applying anchor/tool.

---

## 3. Audio: Veo 3.1 Native Audio (No 3rd-Party VO)

### Strategy

Use **Veo 3.1’s native audio only**—no ElevenLabs, Udio, or other 3rd-party voiceover. Audio is generated **simultaneously with the pixels**, so lip-sync and acoustic physics (e.g. reverb in a marble hall vs. a field) are handled by the model. We avoid timestamp-based SFX (e.g. “Place at 3.2s and 7.5s”), which Veo ignores; instead we use **structured audio blocks** and **Action Anchors** so sound is tied to visuals.

### 3.1. Optimal Audio Block Structure

The Director/Video Agent must use a **modular audio block** in the prompt. Veo responds best when audio is separated from visual instructions with clear tags.

**Template:**
```
Dialogue: "[Character Name] says: 'The exact words in quotes.'"
SFX: "[Specific sound] exactly as [Visual action] happens."
Ambient: "[Background texture description]."
Music: "[Mood], [Genre], [Instruments]."
```

**Example (Biblical Miniature):**
- **Visual:** "Macro shot of a clay-textured Jesus figurine on a wooden mountaintop."
- **Dialogue:** "Jesus says: 'Peace be with you.'"
- **SFX:** "Soft wind whistling through the miniature trees."
- **Ambient:** "Quiet, airy mountaintop atmosphere with a slight echo."
- **Music:** "Cinematic, ethereal orchestral swell with soft strings."

### 3.2. Best Practices for Sync

**A. Action Anchor (SFX)**  
Tie sounds to visuals so Veo syncs transients to frames.

- **Bad:** `SFX: A door slams.`
- **Good:** `SFX: A heavy wooden door slams shut exactly when the character's hand leaves the handle.`

**B. 7-Second Rule (Dialogue)**  
Veo generates in ~4–8s chunks. ~130 wpm ⇒ **~12–15 words per 7s segment**.

- **System rule:** If a segment’s dialogue exceeds **15 words**, the Segment Splitter must **split it into two segments** (or trim/redistribute).

**C. No-Subtitles Guardrail**  
AI video often “visualizes” dialogue as on-screen text.

- **Fix:** Add `(no subtitles, no text overlays)` to the **negative prompt** (or a fixed append to every Veo prompt when `enable_subtitles` is false). For tools, enforce in `video_prompt_template` or Video Generator.

### 3.3. Master Voice Reference

To reduce voice shift between segments, describe the **character’s voice in the global context** of every segment prompt.

- **Example:** *"All dialogue is spoken by a 10-year-old boy with a soft, raspy American accent."*
- **Source:** From `character_reference_sheet`, `lead_character_description`, or Script/Character Reference; inject into `[GLOBAL STYLE ANCHOR]` or a new `[VOICE REFERENCE]` block that Video Generator appends when `enable_audio` is true.

### 3.4. Integration: Audio Slice in Segment Splitter

For each segment, the Segment Splitter (or Script/Technical Editor) must produce an **Audio Slice**:

- `dialogue_cue`: dialogue in that window, formatted as `"[Name] says: '...'"` (≤15 words; split if over).
- `sfx_cue`: SFX tied to a **visual action** in that segment (Action Anchor).
- `ambient_cue`: background texture for that segment.
- `music_cue` (optional): mood, genre, instruments.

These feed `{dialogue_cue}`, `{sfx_cue}`, `{ambient_cue}`, `{music_cue}` in `video_prompt_template`.

### 3.5. Tool Template and Config

- **`audio_strategy`:** `"native_veo"` (or implicit: we do not use 3rd-party VO).
- **New placeholders:** `{dialogue_cue}`, `{sfx_cue}`, `{ambient_cue}`, `{music_cue}` (optional).  
- **Example:**  
  `"A {category} scene. {segment_action}. AUDIO: Dialogue: {dialogue_cue}. SFX: {sfx_cue}. Ambient: {ambient_cue}. (no subtitles, no text overlays)."`

### 3.6. Remove Timestamp-Based SFX

- **Tool Enhancer:** Remove any “Place ‘Bass Drops’ or ‘Sfx Stabs’ at exactly 3.2s and 7.5s” (and similar) from `video_prompt_template`.
- **Video Generator:** Do not append SFX timestamp lines. Strip known timestamp-SFX patterns from legacy tools if present.
- **Script:** Keep `audio_cues`; the Segment Splitter turns them into `sfx_cue` with **Action Anchor** phrasing, not timestamps.

### 3.7. User Input: `enable_audio` (Audio On/Off)

Audio generation **must** be driven by a **user input parameter**. The user turns audio on or off at workflow creation; the system must respect that choice end-to-end.

**Sources (user input):**
- **JSON** `POST /api/v1/generate`: `WorkflowInput.enable_audio` (default: `false`).
- **Form** `POST /api/v1/generate/with-image`: `enable_audio: bool = Form(default=False)`.

**Flow:**
1. **Create:** `enable_audio` is stored in `workflows.enable_audio` (DB).
2. **Run:** `workflow_runner._build_initial_state` and `_build_continue_state` pass `enable_audio` from the workflow row into LangGraph state. Use `workflow.get("enable_audio", False)` when the key is missing (align with “explicit opt-in”).
3. **Video Generator:** `state.get("enable_audio", False)`. When `False`, do **not** request audio from Veo (no Optimal Audio Block, no `[VOICE REFERENCE]`, no `generate_audio` / audio-inclusive options in the Veo API). When `True`, generate Veo native audio as in §3.1–3.6.

**Contract:** Veo generates audio **only** when `enable_audio` is `true`. There is no server-side or default override of the user’s choice.

**Files:** `app/models/workflow.py` (WorkflowInput), `app/api/routes/generate.py`, `app/services/workflow_runner.py`, `app/agents/video_generator.py`. `WorkflowOutput` (GET `/workflows/{id}`) should include `enable_audio` and `enable_subtitles` so clients can see what was set.

### 3.8. Native vs 3rd-Party (Reference; We Use Native)

| Feature | Veo 3.1 Native | 3rd-Party (ElevenLabs/VO) |
|---------|----------------|---------------------------|
| **Lip-sync** | **Perfect** (one stream) | Manual alignment |
| **Physics** | **High** (reverb, room) | Dry; manual reverb/EQ |
| **Voice choice** | Limited (model picks) | Infinite |
| **Consistency** | Medium (may shift between clips) | High |
| **Cost** | **Zero** (included) | High |

### 3.8. Files

- `app/services/tool_enhancer.py`: remove SFX timestamp block; when building video template, use `{dialogue_cue}`, `{sfx_cue}`, `{ambient_cue}` and Action Anchor guidance.
- `app/agents/video_generator.py`: append Optimal Audio Block and `[VOICE REFERENCE]` when `enable_audio`; enforce “no subtitles” in negative or fixed append; accept `dialogue_cue`, `sfx_cue`, `ambient_cue`, `music_cue` from Segment Splitter.
- `app/services/segment_splitter.py` (or in `video_generator`): produce Audio Slice per segment; 7-Second Rule (split/trim if >15 words dialogue).
- `Documentations/veo_prompting_guide.md`: document Veo native audio, Optimal Audio Block, Action Anchor, 7-Second Rule, Master Voice Reference, no-subtitles guardrail; state we do not use 3rd-party VO.

---

## 4. Scene–Segment Mapping and Ghost Time

### Problem

- 8 scenes vs 5 segments; 32s script vs 36s video → “ghost time” at the end (frozen/looping).
- In RABA: `plan_video_segments(duration_seconds)` is duration-based (8s initial + 7s extensions). Veo extensions are ~7s each; we can’t request 3s. Trim does `trim_edges` (0.5s each end), not “cut at `duration_seconds`”.

### Changes

1. **Segment planning**  
   - Keep duration-based `plan_video_segments`. Optionally, later derive a Temporal Map from script `scenes` and align segment boundaries where practical (P2).

2. **Trim Agent and Video Trimmer**  
   - **Target length:** Use `duration_seconds` from workflow or `script_output.total_duration_seconds` when available.
   - **When `video_duration > duration_seconds`:** Add a “trim to length” step: cut at `duration_seconds` (e.g. ffmpeg `-t duration_seconds` or `-to start + duration_seconds`). Keep `trim_edges` (e.g. 0.5s) only if we still want to remove first-frame jitter; otherwise, the hard cut is enough.
   - **Order:** download → if `duration > duration_seconds` then trim to `duration_seconds` → optionally `trim_edges` for jitter.

3. **Files**

   - `app/agents/trim_agent.py`: pass `duration_seconds`; call new trim-to-length when over.
   - `app/services/video_trimmer.py`: e.g. `trim_to_duration(input_bytes, duration_seconds)` or extend `trim_edges` with an option.

---

## 5. Segment Splitter / Technical Editor

### Problem

- Critic wants an agent between Script and Video that produces, per segment: Temporal Window, Script Slice, Anchor State, Goal State, Technical Delta.
- In RABA: no such node; Video Generator does planning and prompt building internally.

### Changes

1. **Segment Splitter as a helper**  
   - New `app/services/segment_splitter.py` or logic inside `app/agents/video_generator.py`.  
   - **Function:** `compute_segment_context_blocks(script_output, segment_plans) -> list[SegmentContextBlock]`.  
   - **SegmentContextBlock:**  
     `segment_index`, `total_segments`, `start_time`, `end_time`, `segment_script`, `segment_action`, `anchor_state`, `goal_state`, `technical_delta` (optional),  
     **Audio Slice:** `dialogue_cue`, `sfx_cue`, `ambient_cue`, `music_cue` (optional). Dialogue must be **≤15 words** per segment (7-Second Rule); if over, split the segment or trim/redistribute. SFX must use **Action Anchor** phrasing (tied to a visual action).

2. **Implementation**  
   - **Simple:** Reuse `build_video_prompt`’s `relevant_scenes` to build `segment_script`; derive `dialogue_cue` from scene `dialogue`, `sfx_cue` from `audio_cues` with Action Anchor phrasing; `anchor_state` = previous `goal_state`; `goal_state` = last scene in window or 1-line summary.  
   - **Richer (optional):** Gemini “Technical Editor” prompt to produce `segment_action`, `anchor_state`, `goal_state`, `technical_delta`, and Audio Slice per segment. Can store in state as `segment_context_blocks` for HITL/debug.

3. **Optional LangGraph node**  
   - A dedicated “Technical Editor” node between Script and Video is optional; the same behavior can live inside Video Generator.

4. **Files**

   - `app/services/segment_splitter.py` (new) or `app/agents/video_generator.py`.

---

## 6. Image Generation: Master Style Frame, Negative Constraints, and Veo Reference

*(Critical analysis: we adopt the spirit of the critic’s “Anchor” and “Negative Prompt” ideas, corrected for our stack. “Reference to every segment” is not supported by Veo’s extension API.)*

### 6.1. What the Critic Proposed

1. **Beat Sheet from Research** – map concepts to time-blocks; **every 5 seconds = 1 Visual Change Request (VCR)**. For 30s → 6 VCRs.  
2. **Master Style Frame** – generate one canonical image (Nano Banana Pro) **before** the video; use a **Negative Prompt Generator** so it’s free of text and artifacts; pass it as **mandatory_reference_image to the video model for every segment**.

### 6.2. Evidence from Web and Docs

**Beat Sheet / VCR**  
- Beat sheets (Save the Cat, etc.) map **narrative** beats and **visual change** (e.g. Opening Image vs Final Image). The critic’s “1 VCR per 5s” is a **time-based pacing** rule that fits short-form: it forces a distinct visual turn every ~5s and reduces “wall of same” in the middle.  
- **Conclusion:** Adopt. Research should output a **Beat Sheet** with `vcr_count = ceil(duration_seconds/5)` and `beats[]` with `t_start`, `t_end`, `concept`, `suggested_vcr`. Script (and Segment Splitter) consume it so scenes and segments align with those visual turns. **Image** benefits **indirectly**: better scene structure and VCR-aligned descriptions yield clearer, more varied prompts.

**Master Style Frame**  
- A single, style- and character-anchoring image before video gives Veo a strong reference for the **first** segment. Industry practice (e.g. Google’s Veo examples) uses 1–3 reference images for the **initial** generation only.  
- **Conclusion:** Adopt **one Master Style Frame** as the **only** generated image. One Nano call; no per-scene images. The Master anchors style and character for the initial Veo segment; segment prompts carry narrative. Per-scene images are **omitted** to keep one canonical look and to reduce cost and complexity.

**“mandatory_reference_image to the video model for every segment”**  
- **Veo API (veo_doc.md, web):**  
  - **Initial** `generate_videos`: supports `image` (first frame), `referenceImages` (up to 3).  
  - **Extension** `generate_videos(..., video=prev, prompt=...)`: only `video` and `prompt`; **no** `image` or `referenceImages`.  
- **Conclusion:** Passing a reference image to **every** segment is **not supported**. We pass the **Master** (only generated image) to the **initial segment only**. For extensions we rely on `video=previous_video` (Veo uses the last ~24 frames) and strong **text** continuity (`previous_segment_state`, `[GLOBAL STYLE ANCHOR]`, `[REFERENCE IMAGES]` as textual description). We do **not** promise “every segment” in the plan.

**Negative Prompt Generator / “free of text and artifacts”**  
- **Gemini image API (Nano Banana, nanao_banana_doc, web):** There is **no** `negativePrompt` (or equivalent) in `gemini-2.5-flash-image` or `gemini-3-pro-image-preview`. Legacy Imagen on Vertex has it; Gemini image models do not.  
- **Recommended approach (Google, community):** Use **in-prompt negative constraints**—a clear sentence at the end of the prompt, e.g. *“The image must be free of text, watermarks, labels, lettering, and graphical overlays. No artifacts or distorted elements.”*  
- **Conclusion:** We implement a **Negative Constraint Block** (fixed or from a tiny generator) **appended to the prompt**, not a separate API field. This acts as our “Negative Prompt Generator” for the Master Style Frame and, optionally, all generated images.

### 6.3. Concrete Changes to the Image Generation Step

1. **Negative Constraint Block**  
   - Append to the **Master** prompt a fixed suffix, e.g.:  
     *“The image must be free of text, watermarks, labels, lettering, and UI overlays. No artifacts, distorted elements, or unintended graphical additions.”*  
   - Optional: tool-level `image_negative_constraint` to override or extend; default = the fixed block.  
   - **Files:** `app/agents/image_generator.py` (append before calling Nano), `app/services/nano_banana.py` (only if we centralize prompt post-processing there).

2. **Master Style Frame (one image only)**  
   - **Flow:** Make **one** Nano call to create a **Master Style Frame**. **No per-scene images.**  
   - **Prompt:** From `global_style_anchor` + `character_reference_sheet` (if present) + `selected_tool` + `topic`. Focus on: **style** (palette, materials, lighting, camera), **character** (face, costume, key traits), **one representative moment** (e.g. hook or first beat). It is a **style and character anchor**. Append the **Negative Constraint Block**.  
   - **Output:** One image URL. `generated_images = [master_url]`. This is the **only** reference passed to Veo for the **initial** segment. For extensions, Veo’s API does not accept images; we use `video=prev` and text continuity (`[GLOBAL STYLE ANCHOR]`, `[REFERENCE IMAGES]` as description).

3. **Reference image only for the initial segment**  
   - **Initial segment:** Pass the Master (only generated image) as `referenceImages` or `image` (first frame). `generated_images = [master_url]`.  
   - **Extensions:** Veo’s API does **not** accept images. Rely on `video=previous_video` and text: `previous_segment_state`, `[GLOBAL STYLE ANCHOR]`, `[REFERENCE IMAGES]` (short textual description of the Master for continuity).  
   - **Docs:** In the plan and in `veo_prompting_guide.md`, state that we use **one** reference (Master) for the **initial** segment only; extensions use video and text.

4. **Optional: `image_negative_constraint` in tools**  
   - Add an optional `image_negative_constraint` (or re-use a generic “negative” blob) on the tool. If set, append it (or merge with the default block) to image prompts. Gives per-tool control (e.g. “no religious symbols” for some tools) without a separate Negative Prompt API.

### 6.4. Files

- `app/agents/image_generator.py`:  
  - Add **Negative Constraint Block** (fixed default); append to the Master prompt.  
  - **Master Style Frame only:** one Nano call; build prompt from anchor + character + tool + topic; append Negative Constraint. **No per-scene images.** `generated_images = [master_url]`.  
  - **Persistence (§6.6):** call `_persist_to_database` with the Master output. In `workflows.generated_images.images[]` and in `media.metadata` set `"role": "master_style_frame"`.  
  - Optional: read `image_negative_constraint` from `selected_tool`.  
- `app/services/nano_banana.py`: no API change; optionally a helper to append the Negative Constraint if we want it in one place.  
- `app/agents/video_generator.py`: it uses `select_reference_images(generated_images)`. With `generated_images = [master_url]`, only the Master is passed to the initial segment. No change to extension logic (no images).  
- `Documentations/nano_prompt_guide.md`: document the Negative Constraint Block and Master Style Frame; note that Gemini image has no `negativePrompt` and we use in-prompt constraints.  
- `Documentations/veo_doc.md` or `veo_prompting_guide.md`: state that reference images are for the **initial** segment only; extensions use `video=prev` and text continuity.

### 6.5. Relation to Beat Sheet (§10)

Research’s **Beat Sheet** (VCR every ~5s) does **not** feed Image directly. Script consumes it and produces VCR-aligned scenes → **Master Style Frame** prompt gets clearer, more varied inputs (e.g. first beat / “Hook / Opening image”). We use **one Master only**; no per-scene images.

### 6.6. Database Persistence for Master

The Master image **must** be saved to the database so it can be read by Video Generator, HITL, workflows API, and continue-from-failed.

**workflows.generated_images (JSONB)**  
- **`images`:** `[{ ...GeneratedImage.model_dump(), "role": "master_style_frame" }]`. For Master-only, a single element.  
- **`total_count`:** `1`.  
- **`all_image_urls`:** `[master_url]`.  
- **`generation_time_ms`**, **`model_used`:** as today.  

**media table**  
- One row per generated image. For Master:  
  - `workflow_id`, `media_type: "image"`, `source: "generated"`  
  - `storage_url`, `storage_path`  
  - **`metadata`:** include `"role": "master_style_frame"`, plus `prompt` (truncated), `model_used`, `aspect_ratio`, `resolution`. For `GeneratedImage` use `scene_number=1` (required by model); persist `role` in `media.metadata` for clarity.

**Image Generator**  
- Call `_persist_to_database(workflow_id, output)` with `ImageGeneratorOutput` containing the single Master in `generated_images`. Ensure `GeneratedImage` supports `scene_number=1` for Master (or add optional `role` to the model and set `role="master_style_frame"` when building the output). When writing to `media`, set `metadata["role"] = "master_style_frame"`.

**Files**  
- `app/agents/image_generator.py`: ensure `_persist_to_database` is invoked for Master output; when building `GeneratedImage` for Master, pass `scene_number=1` (or add `role` to the model). When inserting into `media`, set `metadata.role = "master_style_frame"`.  
- `app/models/image.py`: optional `role: Optional[str] = None` on `GeneratedImage`; if present, include in `model_dump` and in `media.metadata`.

---

## 7. Tool Template Placeholders (Stateful Templates)

### Problem

- `video_prompt_template` only has `{script}` and `{duration}`; critic wants segment-level variables.

### Changes

1. **New placeholders for `video_prompt_template`**  
   - **Segment:** `{segment_index}` (0-based), `{total_segments}`, `{segment_script}` or `{segment_action}`, `{previous_segment_state}` or `{continuity_from}`.  
   - **Audio (Veo native):** `{dialogue_cue}`, `{sfx_cue}`, `{ambient_cue}`, `{music_cue}` (optional). Filled from Segment Splitter’s Audio Slice.  
   - **Config:** `audio_strategy: "native_veo"` (tool-level or system default; no 3rd-party VO).

2. **PromptBuilder**  
   - Treat these as optional. If a template doesn’t use them, keep `{script}` and `segment_info` as today.

3. **Video Generator**  
   - Always fill the new placeholders when using a segment-specific block (from Segment Splitter): segment + **Audio Slice** (`dialogue_cue`, `sfx_cue`, `ambient_cue`, `music_cue`). Prefer segment block over `{script}` when both exist. When `enable_audio` is true, append Optimal Audio Block and `[VOICE REFERENCE]` (§3).

4. **DB and validation**  
   - Migration or tool schema: allow and document new placeholders. Validation (e.g. in `tools` routes) can allow either `{script}` or the new set.

5. **Files**

   - `app/models/tool.py`: document new placeholders.
   - `app/agents/video_generator.py`: pass them in render context.
   - `Documentations/API_Docs/03_TOOLS.md`: document `video_prompt_template` placeholders.

---

## 8. Last-Frame as `image_input` for Extensions

### Problem

- Critic: use the last frame of Segment N as `image_input` for Segment N+1.
- In RABA: `extend_video` takes `video=actual_video`. The API extends from the existing video (last ~24 frames). There is no `image` parameter for `extend_video`.

### Conclusion

- **No code change** for “last-frame as image” on extensions.  
- We already get continuity via `video=previous_video`. Focus on **prompt content**: segment-specific `segment_action`, `previous_segment_state`, and `[GLOBAL STYLE ANCHOR]` / `[REFERENCE IMAGES]` in extension prompts.

---

## 9. Assembly Line (Layers A–D)

### Target (Veo 3.1 Native Audio)

- **A:** Clean Video (Veo).  
- **B:** **Veo 3.1 Native Audio**—dialogue, SFX, ambient, music via Optimal Audio Block and Action Anchor in the prompt. **No 3rd-party VO (ElevenLabs, etc.).**  
- **C:** Text Overlays (Overlay + Compositor) when `enable_subtitles`.  
- **D:** **Veo native SFX**—SFX described in the prompt and tied to visuals via Action Anchor; **no post-video SFX stitching.**

### RABA Today

- **A:** Veo + Trim.  
- **B:** Veo `enable_audio`; we will add structured audio blocks (Dialogue, SFX, Ambient, Music) and Master Voice Reference.  
- **C:** Overlay + Compositor for subtitles when `enable_subtitles`.  
- **D:** SFX via Veo prompt (Action Anchor), not timestamps or a separate agent.

### Changes

- **A, C:** Keep as-is.  
- **B:** Use **Veo 3.1 native** only: Optimal Audio Block (§3.1), 7-Second Rule, Master Voice Reference; no ElevenLabs/VO agent.  
- **D:** Use **Veo native** for SFX via Action Anchor in the prompt; remove timestamp-based SFX; no Dedicated Audio Agent.

---

## 10. Research: Beat Sheet and Visual Change Requests (VCR)

*(Step 1 from the critic: “Structural Research & The Beat Sheet.” We adopt it and clarify how it improves Script, Segment Splitter, and indirectly Image.)*

### 10.1. What the Critic Proposed

- **Instead of a “simple research dump”:** Research must output a **Beat Sheet** that maps concepts to **time-blocks**.  
- **Rule:** Every **5 seconds** there must be a **Visual Change Request (VCR)**. For a 30s script → 6 unique VCRs.

### 10.2. Why It Helps

- **Beat sheets** (Save the Cat, etc.) are standard: they map narrative beats and **visual change** (e.g. Opening Image vs Final Image). For short-form, “1 VCR per 5s” is a **pacing** rule: it forces a clear visual turn every ~5s and reduces long stretches without a change.  
- **Research** already produces `research_data` (and `research_images`). Adding a **Beat Sheet** gives Script and Segment Splitter a **temporal scaffold**: when to change shot, subject, or idea.  
- **Image** benefits **indirectly**: Script’s scenes become VCR-aligned → clearer, more varied scene descriptions → better image prompts and a Master Style Frame that sits above those beats.

### 10.3. Beat Sheet Schema (Research Output)

Add to Research output (e.g. `research_data.beat_sheet` or a dedicated `beat_sheet` in state):

```json
{
  "duration_seconds": 30,
  "vcr_count": 6,
  "beats": [
    { "t_start": 0,  "t_end": 5,  "concept": "Hook / Opening image",     "suggested_vcr": "Reveal core paradox or subject" },
    { "t_start": 5,  "t_end": 10, "concept": "First development",       "suggested_vcr": "Scale or angle change; new detail" },
    { "t_start": 10, "t_end": 15, "concept": "Conflict or contrast",    "suggested_vcr": "Introduce tension or comparison" },
    { "t_start": 15, "t_end": 20, "concept": "Peak / midpoint",         "suggested_vcr": "Strongest visual or idea" },
    { "t_start": 20, "t_end": 25, "concept": "Resolution or twist",     "suggested_vcr": "Shift toward conclusion" },
    { "t_start": 25, "t_end": 30, "concept": "CTA / Closing image",     "suggested_vcr": "Call to action or mirror opener" }
  ]
}
```

- **`vcr_count`:** `ceil(duration_seconds / 5)`.  
- **`beats`:** One entry per ~5s block; `concept` is narrative/theme; `suggested_vcr` is a one-line **visual** change (camera, subject, scale, mood) that Script and Segment Splitter should respect when building scenes and segment actions.

### 10.4. How Downstream Use It

- **Script Writer:** Consume `beat_sheet`. Ensure scenes (or scene boundaries) align with `beats` and that each beat’s `suggested_vcr` is reflected in at least one scene’s visual (camera, action, or mood). Script can still output a **Temporal Map** (e.g. `segment_boundaries`, `vcr_per_segment`) derived from `scenes` and `duration_seconds` for the Segment Splitter.  
- **Segment Splitter:** Use `beat_sheet` and/or Script’s Temporal Map so segment boundaries and `segment_action` / `goal_state` align with VCRs. Reduces “same shot” across a full 7s segment.  
- **Image Generator:** No direct consumption. Better scene structure and VCR-aligned descriptions improve the **Master Style Frame** prompt indirectly.

### 10.5. Implementation (P2)

- **Deep Research (or Creative Ideation) output:** When `duration_seconds` is known (from workflow or default), compute `vcr_count` and `beats`. For **FACTUAL** and **HYBRID**, concepts can be grounded in `research_data`; for **CREATIVE**, derive from topic + tool. A simple template or a short Gemini call can fill `concept` and `suggested_vcr` per 5s block.  
- **State:** `beat_sheet` in `research_data` or top-level in state; Script and Segment Splitter read it.  
- **Files:** `app/agents/deep_research.py`, `app/services/deep_research.py` or `app/services/creative_ideation.py`; `app/graph/state.py` (optional `beat_sheet` field); Script and Segment Splitter to consume.

---

## 11. State Inheritance

### Critic

1. Visual seed/reference from Segment 0 passed to all.  
2. Environmental persistence (e.g. “mountain on left”).  
3. Lighting momentum (e.g. 5600K → 4500K across segments).

### RABA

- We pass `generated_images` and `character_reference_sheet` into the **initial** segment; for extensions we only have `video=prev` and text. We already append `[GLOBAL STYLE ANCHOR]` and `[REFERENCE IMAGES]` to extension prompts.

### Changes

1. **Visual/reference:** Keep passing same refs to initial segment; for extensions, keep and enforce `[GLOBAL STYLE ANCHOR]` and `[REFERENCE IMAGES]` in the prompt.  
2. **Environment:** Segment Splitter (or Technical Editor) can add short hints like “Maintain mountain on left frame-edge” into `segment_action` or `previous_segment_state` when the script implies it.  
3. **Lighting:** If the script has a clear progression (e.g. sunset), add to `segment_action`/`goal_state` lines like “Segment N: 5600K → 4500K” (P2).  
4. **Master Voice Reference (audio):** In the **global context of every segment** when `enable_audio` is true, append a `[VOICE REFERENCE]` (or fold into `[GLOBAL STYLE ANCHOR]`): *“All dialogue is spoken by [character voice description]”* (e.g. from `character_reference_sheet`, `lead_character_description`). Reduces voice shift between segments.

---

## 12. Tool Enhancer and Tool Creator

When we **create** or **enhance** tools, the Tool Enhancer (`app/services/tool_enhancer.py`) and Tool Creator flows must emit templates that align with this plan. Otherwise new or improved tools keep SFX timestamps, generic “35mm Anamorphic,” and old placeholders.

### 12.1. `video_prompt_template`

| Change | Detail |
|--------|--------|
| **Placeholders** | Require or encourage: `{segment_index}`, `{total_segments}`, `{segment_action}`, `{previous_segment_state}`; and for audio: `{dialogue_cue}`, `{sfx_cue}`, `{ambient_cue}` (optional `{music_cue}`). Keep `{script}` and `{duration}` for legacy. |
| **Remove** | Any “Place ‘Bass Drops’ or ‘Sfx Stabs’ at exactly 3.2s and 7.5s” or similar **timestamp-based SFX** instructions. |
| **Add** | **Optimal Audio Block** (Dialogue, SFX with Action Anchor, Ambient, Music) and “(no subtitles, no text overlays)” when we don’t want burns. `audio_strategy: "native_veo"` in tool config or docs. |
| **Optics** | **Category-specific lens only.** `stylized_3d` → Tilt-Shift 35/50mm; **never** Anamorphic. `surreal_realism` → Anamorphic 14–24mm. `high_octane_anime` → Long 85–200mm. Remove generic “35mm Anamorphic” for all. |

### 12.2. `image_prompt_template`

| Change | Detail |
|--------|--------|
| **Optics** | Same category presets; for `stylized_3d` **never** Anamorphic. |
| **Negative constraints** | Align “Negative Constraints” with our **Negative Constraint Block** (no text, watermarks, labels, artifacts). Optional: `{image_negative_constraint}` for tool-specific exclusions. |
| **Master / style** | Template supports `{scene_description}`, `{style}`. We generate **one Master only** (style+character anchor); the `image_prompt_template` can be used for that Master prompt or deprecated for per-scene if we fully move to Master-only. |

### 12.3. `script_prompt_template` (optional)

- Encourage **VCR-aligned** structure (e.g. a clear visual change every ~5s) so it fits the Beat Sheet.

### 12.4. Validation (Tools API)

When creating/updating tools:

- **video_prompt_template:** (a) “Segment-aware” tools: at least `{segment_action}`, `{previous_segment_state}` and `{dialogue_cue}`, `{sfx_cue}`, `{ambient_cue}` (or accept legacy `{script}`, `{duration}`). (b) Reject or strip templates that still contain timestamp-based SFX phrasing.  
- **image_prompt_template:** Require `{scene_description}`, `{style}`; optional `{image_negative_constraint}`. Ensure a “Negative Constraints” block or that we append our fixed block in code.

### 12.5. Files

- **`app/services/tool_enhancer.py`:** Update `TOOL_ENHANCEMENT_SYSTEM_PROMPT` and `TOOL_IMPROVEMENT_SYSTEM_PROMPT`: video section (new placeholders, remove SFX timestamps, Optimal Audio Block + no-subtitles, **category-specific optics**); image section (category-specific optics, Negative Constraint block).  
- **`app/api/routes/tools.py`:** Validation for `video_prompt_template` (placeholders, no SFX timestamps) and `image_prompt_template` (placeholders, negative block).  
- **`app/models/tool.py`:** Optional `image_negative_constraint`, `audio_strategy` (default `"native_veo"`).  
- **`Documentations/API_Docs/03_TOOLS.md`:** Document new placeholders, `image_negative_constraint`, `audio_strategy`, and “segment-aware” vs legacy `video_prompt_template`.

---

## 13. Visual Logic Cheat Sheet

Use in Global Style Anchor, Segment Splitter, and tool design:

| Category | Physics | Lighting | Lens (Enforced) |
|----------|---------|----------|-----------------|
| **stylized_3d** | High friction, tangible | Miniature tilt-shift, soft shadows | **Tilt-Shift 35/50mm** |
| **surreal_realism** | Liquid, impossible scale | Hyper-naturalistic, single source | **Wide Anamorphic 14–24mm** |
| **high_octane_anime** | Momentum, defy gravity | High contrast, neon rim | **Long 85–200mm** |

---

## 14. Implementation Checklist

- [ ] **P0.1** Segment-Specific Video Prompts: Segment Splitter; `segment_script`/`segment_action`/`previous_segment_state` in template and fallback.
- [ ] **P0.2** Optical Presets: category → lens in Global Style Anchor, Tool Enhancer, Image Generator; never Anamorphic in `stylized_3d`.
- [ ] **P0.3** **Veo 3.1 Native Audio:** Optimal Audio Block (Dialogue, SFX, Ambient, Music); Action Anchor for SFX; 7-Second Rule (≤15 words/segment) in Segment Splitter; Master Voice Reference in global context; no-subtitles guardrail; remove timestamp-based SFX (Tool Enhancer, Video Generator). No 3rd-party VO.
- [ ] **P0.4** Trim to `duration_seconds` when video is longer (Trim Agent, Video Trimmer).
- [ ] **P1.1** New `video_prompt_template` placeholders: `{segment_index}`, `{total_segments}`, `{segment_action}`, `{previous_segment_state}`, `{dialogue_cue}`, `{sfx_cue}`, `{ambient_cue}`, `{music_cue}`; docs and validation.
- [ ] **P1.2** Segment Splitter as `app/services/segment_splitter.py` or inside Video Generator; `SegmentContextBlock` with **Audio Slice** (`dialogue_cue`, `sfx_cue`, `ambient_cue`, `music_cue`) and `compute_segment_context_blocks`.
- [ ] **P1.3** State inheritance: keep `[GLOBAL STYLE ANCHOR]` and `[REFERENCE IMAGES]` in extension prompts; **`[VOICE REFERENCE]`** when `enable_audio`; optional env/lighting hints in Segment Splitter.
- [ ] **P1.4** **Image:** Negative Constraint Block (in-prompt: “free of text, watermarks, labels, artifacts”) for all Nano prompts; optional `image_negative_constraint` on tool. **Video:** enforce “(no subtitles, no text overlays)” when `enable_subtitles` is false.
- [ ] **P1.5** **Image:** Master Style Frame as **only** Nano call (1 image; style+character anchor, Negative Constraint). `generated_images = [master_url]`. Use as sole ref for Veo **initial** segment; no per-scene images.
- [ ] **P1.5b** **Image DB:** Persist Master to **workflows.generated_images** (images with `role: "master_style_frame"`, total_count 1, all_image_urls) and to **media** (metadata.role = `"master_style_frame"`). Ensure `_persist_to_database` is called; optionally add `role` to `GeneratedImage`.
- [ ] **P1.6** **Tool Enhancer / Creator (§12):** In `TOOL_ENHANCEMENT_SYSTEM_PROMPT` and `TOOL_IMPROVEMENT_SYSTEM_PROMPT`: (a) **video:** segment + audio placeholders, remove SFX timestamps, Optimal Audio Block + no-subtitles, **category-specific optics**; (b) **image:** category-specific optics, Negative Constraint block. **Validation** in tools API: placeholders, no SFX timestamps. Optional: `image_negative_constraint`, `audio_strategy` on tool model and in 03_TOOLS.
- [ ] **P1.7** **Endpoint logging (§16):** Every route: `log_request_start` at entry and `log_request_end` on **all** exits (success, HTTPException, 5xx). Audit generate, workflows, tools, hitl, monitoring; add `log_request_end` on any missing branch. Add `log_request_start` / `log_request_end` for `GET /health` and `GET /` in `main.py`.
- [ ] **P2** Research: Beat Sheet with `vcr_count`, `beats[]` (`t_start`, `t_end`, `concept`, `suggested_vcr`); Script and Segment Splitter consume it. Temporal Map in Script; consumption in Segment Splitter.

---

## 15. Suggested Priority

| Priority | Item | Impact | Effort |
|----------|------|--------|--------|
| **P0** | §1 Lazy Extension (Segment Splitter + segment-specific prompts) | Stops drift; biggest quality gain | Medium |
| **P0** | §2 Optical Presets | Fixes blur/ inconsistency in miniatures and 3D | Low |
| **P0** | §3 **Veo Native Audio** (Optimal Audio Block, Action Anchor, 7s rule, Master Voice Reference, no-subtitles; remove timestamp SFX) | Lip-sync and acoustic physics; no 3rd-party VO | Medium |
| **P0** | §4 Trim to `duration_seconds` | Removes ghost time at end | Low |
| **P1** | §5 Segment Splitter + **Audio Slice**; §7 placeholders (incl. `dialogue_cue`, `sfx_cue`, `ambient_cue`) | Stateful templates and Veo-ready audio | Medium |
| **P1** | §6 **Image:** Negative Constraint Block; **one Master only** (no per-scene); ref only for initial Veo segment; **§6.6 Master persisted to DB** (workflows.generated_images, media, `role: "master_style_frame"`) | Fewer text/artifacts; strong style/character anchor; 1 Nano call; DB persistence for HITL/continue/API | Medium |
| **P1** | §12 **Tool Enhancer / Creator:** video + image templates, segment/audio placeholders, optical presets, remove SFX timestamps, Optimal Audio Block, Negative Constraint, validation | New/improved tools get plan by default | Medium |
| **P1** | §16 **Endpoint logging:** `log_request_start` / `log_request_end` on every route and all exit paths; add for /health and / | Traceability, latency, and error visibility | Low |
| **P1** | No-subtitles for video when `enable_subtitles` false | Clean frames | Low |
| **P2** | §10 Research: Beat Sheet + VCR; Script/Segment Splitter consume | Pacing; VCR-aligned scenes; better Image prompts indirectly | Medium |

---

## 16. Endpoint Logging

Every API endpoint must have **request/response logging** so we can trace calls, latency, and errors.

### 16.1. Required Pattern

- **At entry:** `log_request_start(logger, METHOD, path, { key params }` e.g. `{"workflow_id": id}` or `{"topic": topic[:60]}`.  
- **On every exit:** `log_request_end(logger, METHOD, path, status_code, duration_ms)`. This includes: success (200, 201, 204), client errors (400, 404, 422), and server errors (500, 503). **No path should return without `log_request_end`.**  
- **Errors:** `log_error_msg` or `log_warning_msg` before raising `HTTPException` or returning an error response.  
- **Success:** `log_success` or `log_key_value` for important outcomes where useful.

### 16.2. Routes to Audit

| Route file | Endpoints | Notes |
|------------|-----------|-------|
| `workflows.py` | GET /workflows, GET /workflows/{id}, DELETE, POST continue, POST purge-media | Already use log_request_start/end; verify all branches. |
| `tools.py` | GET list, GET {id}, POST create, POST preview, PUT {id}, POST improve, DELETE, POST execute, POST bulk-update, PUT prompts | Same. |
| `generate.py` | POST (JSON), POST (multipart) | `_create_workflow_inner` has `log_request_start`; ensure `log_request_end` on **all** exits (success and HTTPException). |
| `hitl.py` | POST feedback, GET gate, GET gates | Same. |
| `monitoring.py` | GET summary, GET video/{id}, GET pricing | Same. |
| `main.py` | GET /health, GET / | Currently `logger.debug` only. Add `log_request_start` and `log_request_end` (with status 200 and duration) for consistency. |

### 16.3. Implementation

- **generate.py:** In `_create_workflow_inner`, wrap the handler in a try/except/finally or ensure every `raise HTTPException` and `return` path calls `log_request_end` with the correct status. If the route decorator does not catch HTTPException, the inner function must log before raising.  
- **main.py /health and /:** Add `log_request_start(logger, "GET", "/health", {})` at start and `log_request_end(logger, "GET", "/health", 200, duration_ms)` before return; same for `/`.  
- **All routes:** Confirm no handler returns or raises without a prior `log_request_end` (or a central middleware that logs on response; if we rely on per-route logging, every branch must call it).

### 16.4. Files

- `app/api/routes/generate.py`: add `log_request_end` on all exit paths of `_create_workflow_inner` (and the multipart handler if it differs).  
- `app/main.py`: add `log_request_start` / `log_request_end` for `GET /health` and `GET /`.  
- `app/api/routes/workflows.py`, `tools.py`, `hitl.py`, `monitoring.py`: audit; add `log_request_end` on any missing branch (e.g. unhandled exception that doesn’t go through a common handler).  
- `app/utils/logging.py`: ensure `log_request_start` and `log_request_end` exist and accept the signature above.

---

## 17. References

- `Backend/sys_imp_guide.md` – Chief Critic analysis.
- Web: Beat Sheet (Save the Cat, studio practice); Veo 3.1 reference images and extension (no `image`/`referenceImages` on extend); Gemini/Nano Banana: no `negativePrompt`; use in-prompt negative constraints; Vertex “Omit content using a negative prompt” (legacy Imagen only).
- `Backend/app/agents/video_generator.py` – `plan_video_segments`, `build_video_prompt`, `build_extension_prompt`, template rendering.
- `Backend/app/agents/image_generator.py` – Nano Banana, `image_prompt_template`.
- `Backend/app/agents/global_style_anchor.py` – `camera`, style anchors.
- `Backend/app/services/veo.py` – `generate_video`, `extend_video`.
- `Backend/app/services/tool_enhancer.py` – image/video templates, SFX and Anamorphic.
- `Backend/app/services/video_trimmer.py` – `trim_edges`.
- `Backend/migrations/006_update_seed_tools_prompts.sql` – seed `video_prompt_template`, `image_prompt_template`.
- `Backend/Documentations/veo_prompting_guide.md`, `nano_prompt_guide.md`.
