# RABA Architectural Critique Analysis & Improvement Roadmap

**Status**: Deep Analysis & Production Recommendations  
**Date**: January 2026  
**Context**: Analysis of critique received for complex "liquid-morphing" Tesla evolution video

---

## Executive Summary

This document analyzes an architectural critique of RABA's video generation system, maps each issue to current system components, and proposes production-grade solutions. The critique highlights limitations in handling complex temporal transformations, text rendering, and audio-visual synchronization.

---

## Table of Contents

1. [Critique Summary](#critique-summary)
2. [Issue 1: Linear Workflow Limitations](#issue-1-linear-workflow-limitations)
3. [Issue 2: Temporal & Motion Consistency](#issue-2-temporal--motion-consistency)
4. [Issue 3: Text Rendering Failures](#issue-3-text-rendering-failures)
5. [Issue 4: Tool Repository Gaps](#issue-4-tool-repository-gaps)
6. [Issue 5: Audio-Visual Synchronization](#issue-5-audio-visual-synchronization)
7. [Implementation Roadmap](#implementation-roadmap)

---

## Critique Summary

| Critique Area | Current RABA State | Gap Severity |
|--------------|-------------------|--------------|
| Orchestration (PVR) | Linear LangGraph flow | **High** |
| Temporal Consistency (CAG) | No cross-attention guidance | **High** |
| Scene Parsing (CSP) | Monolithic prompt handling | **Medium** |
| Text Rendering (ST) | Relies on Veo hallucination | **Critical** |
| Temporal Tracking | No DiffTrack integration | **Medium** |
| Physics-Driven Motion | No ReVision-style logic | **Medium** |
| Subject Referencing | pgvector exists but underutilized | **Low** |
| Audio-Visual Sync | Veo 3.1 native, but limited control | **Medium** |

---

## Issue 1: Linear Workflow Limitations

### Critique
> "The current LangGraph-based orchestrator manages a linear flow (Intent → Research → Script → Image → Video). This architecture lacks the compositional feedback loops required for complex transformations."

### Current RABA Implementation

**Location**: `app/graph/workflow.py`, `app/services/workflow_runner.py`

```python
# Current linear flow
StateGraph:
  intent_tool_selector → deep_research → script_writer → 
  image_generator → video_generator → output_processor
```

**Problem**: Single-pass video generation cannot iteratively refine complex transformations like "liquid-morphing." Once a segment is generated, there's no feedback loop to improve it.

### Recommendation: Progressive Video Refinement (PVR) Module

**Proposed Architecture**:

```python
# New iterative refinement flow
class ProgressiveVideoRefinement:
    """Multi-pass video generation with quality feedback loops."""
    
    async def generate_with_refinement(
        self,
        state: VideoGenerationState,
        max_iterations: int = 3,
        quality_threshold: float = 0.85,
    ) -> VideoGeneratorOutput:
        """
        Iteration 1: Coarse motion generation (low resolution, fast)
        Iteration 2: Motion refinement (higher resolution)
        Iteration 3: Detail enhancement (full resolution, slow)
        """
        for iteration in range(max_iterations):
            # Generate at current quality level
            video = await self._generate_pass(state, iteration)
            
            # Evaluate quality using Gemini vision
            quality_score = await self._evaluate_quality(video, state)
            
            if quality_score >= quality_threshold:
                break
            
            # Generate refinement feedback for next pass
            state["refinement_feedback"] = await self._get_refinement_feedback(
                video, state, quality_score
            )
        
        return video
```

**Files to Modify**:
- `app/agents/video_generator.py` - Add PVR wrapper
- `app/services/veo.py` - Add quality evaluation
- `app/graph/workflow.py` - Add conditional refinement nodes

**Implementation Effort**: High (2-3 weeks)

---

## Issue 2: Temporal & Motion Consistency

### Critique
> "Standard video transformers often struggle with maintaining identity consistency during long-duration shots or complex physical interactions like morphing."

### Current RABA Implementation

**Location**: `app/agents/video_generator.py:168` - Temporal Consistency Protocol

```python
# Current approach: Prompt-based consistency
"Temporal Consistency Protocol": 
    "Specify 'Motion Bucket' value (1-10) and define 
     'Start Frame Reference' and 'End Frame Goal'"
```

**Problem**: Prompt-based instructions are suggestions, not guarantees. Veo can still produce "flickering" or "appearance drift" during complex morphing sequences.

### Recommendation A: Cross-Attention Guidance (CAG)

**Current Limitation**: We use Veo 3.1 as a black-box API. CAG requires access to the DiT (Diffusion Transformer) attention layers, which Veo doesn't expose.

**Workaround - Reference Image Anchoring**:

```python
# Enhanced reference image strategy for consistency
class TemporalConsistencyManager:
    """Use keyframe anchoring to maintain identity across segments."""
    
    def __init__(self):
        self.keyframe_interval = 3  # seconds
    
    async def generate_consistency_anchors(
        self,
        script_output: dict,
        duration_seconds: int,
    ) -> list[str]:
        """Generate keyframe images at regular intervals as anchors."""
        num_keyframes = math.ceil(duration_seconds / self.keyframe_interval)
        
        anchors = []
        for i in range(num_keyframes):
            timestamp = i * self.keyframe_interval
            scene_at_timestamp = self._get_scene_at_time(script_output, timestamp)
            
            # Generate keyframe with explicit identity markers
            keyframe_prompt = self._build_identity_preserving_prompt(
                scene_at_timestamp,
                previous_anchor=anchors[-1] if anchors else None,
            )
            
            keyframe = await self.image_service.generate(keyframe_prompt)
            anchors.append(keyframe)
        
        return anchors
```

### Recommendation B: Compositional Scene Parser (CSP)

**Location**: Currently missing - prompts are monolithic blocks

**Proposed Implementation**:

```python
class CompositionalSceneParser:
    """Decompose prompts into hierarchical scene graphs with temporal annotations."""
    
    def parse_to_scene_graph(
        self,
        topic: str,
        script_output: dict,
    ) -> SceneGraph:
        """
        Convert:
          "Tesla evolution from 2008 Roadster to Model S"
        
        Into:
          SceneGraph:
            - Entity: "2008 Roadster" @ 0.0s-4.0s
            - Transition: "liquid-morph" @ 4.0s-6.0s
            - Entity: "2012 Model S" @ 6.0s-10.0s
            - ...
        """
        return SceneGraph(
            entities=self._extract_entities(topic),
            transitions=self._extract_transitions(script_output),
            temporal_anchors=self._build_temporal_anchors(script_output),
        )
    
    def build_segment_prompt(
        self,
        scene_graph: SceneGraph,
        segment_index: int,
        segment_duration: float,
    ) -> str:
        """Build segment-specific prompt with explicit temporal constraints."""
        segment_start = segment_index * segment_duration
        segment_end = segment_start + segment_duration
        
        # Get entities active in this segment
        active_entities = scene_graph.get_entities_in_range(
            segment_start, segment_end
        )
        
        # Get transitions occurring in this segment
        active_transitions = scene_graph.get_transitions_in_range(
            segment_start, segment_end
        )
        
        return self._format_segment_prompt(
            active_entities,
            active_transitions,
            segment_start,
            segment_end,
        )
```

**Files to Create**:
- `app/services/scene_parser.py` - CSP implementation
- `app/models/scene_graph.py` - Scene graph data models

**Implementation Effort**: Medium (1-2 weeks)

---

## Issue 3: Text Rendering Failures

### Critique
> "Your requirement for 'model name and year on screen' is a known failure point for standard T2V models, which often produce distorted or illegible typography."

### Current RABA Implementation

**Location**: `app/agents/video_generator.py`, `app/services/veo.py`

**Problem**: RABA relies on Veo to "hallucinate" text from prompt instructions. This consistently produces:
- Distorted characters
- Illegible typography
- Floating/misaligned text

### Recommendation: Structured Text (ST) Representation + Post-Processing

**Two-Track Approach**:

#### Track A: Prevent Text in Veo Generation

Already implemented in our instruction-following fixes:
```python
# In video prompt
if not enable_subtitles:
    parts.append("Text: NO TEXT OVERLAYS, no subtitles, no captions, no on-screen text\n")
```

#### Track B: Add Text in Post-Processing with FFmpeg

**New Service**: `app/services/text_overlay.py`

```python
class TextOverlayService:
    """Add typographically correct text overlays using FFmpeg."""
    
    def __init__(self):
        self.font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    
    async def add_text_overlays(
        self,
        video_bytes: bytes,
        overlays: list[TextOverlay],
    ) -> bytes:
        """
        Add text overlays to video using FFmpeg drawtext filter.
        
        Args:
            video_bytes: Input video
            overlays: List of TextOverlay(text, start_time, end_time, position, style)
        
        Returns:
            Video bytes with text overlays
        """
        filter_chain = self._build_drawtext_filter(overlays)
        
        cmd = [
            "ffmpeg", "-y", "-i", "input.mp4",
            "-vf", filter_chain,
            "-c:a", "copy",
            "output.mp4"
        ]
        # Execute and return
```

**Text Overlay Data Model**:

```python
class TextOverlay(BaseModel):
    """Structured text overlay specification."""
    text: str
    start_time: float  # seconds
    end_time: float
    position: tuple[int, int]  # x, y coordinates
    font_size: int = 48
    font_color: str = "white"
    background_color: Optional[str] = "black@0.5"
    animation: Optional[str] = "fade_in"  # fade_in, slide_up, etc.
```

**Integration with Script Writer**:

When `enable_subtitles=True`, the script writer should output a `text_overlays` field:

```python
# In ScriptOutput model
class ScriptOutput(BaseModel):
    # ... existing fields ...
    text_overlays: list[TextOverlay] = Field(
        default_factory=list,
        description="Structured text overlays to add in post-processing"
    )
```

**Files to Create**:
- `app/services/text_overlay.py` - FFmpeg-based text overlay service
- `app/models/text_overlay.py` - Text overlay data models

**Files to Modify**:
- `app/models/script.py` - Add text_overlays field
- `app/agents/script_writer.py` - Generate structured text overlays
- `app/agents/video_generator.py` - Apply text overlays in post-processing

**Implementation Effort**: Medium (1-2 weeks)

---

## Issue 4: Tool Repository Gaps

### Critique
> "Your Tool Repository requires new specialized capabilities: Temporal Tracking Tool, Physics-Driven AI Plugin, Vector Database for Subject Referencing."

### Current RABA Implementation

**Location**: `app/tools/registry.py`, `app/models/tool.py`

**Current Tools**:
- Impossible Simulations (realistic)
- Concept Combat (anime)
- Data Dioramas (animation)

**Gap**: No specialized tools for temporal tracking, physics simulation, or identity preservation.

### Recommendation A: Temporal Tracking Tool (DiffTrack-style)

**Concept**: Track visual elements across frames to verify consistency.

**Implementation Approach** (using Gemini Vision):

```python
class TemporalTrackingTool:
    """
    Use Gemini Vision to track visual elements across video frames.
    Verifies identity consistency without requiring DiffTrack integration.
    """
    
    async def verify_consistency(
        self,
        video_bytes: bytes,
        tracking_targets: list[str],  # e.g., ["Tesla Roadster", "3/4 camera angle"]
        sample_interval: float = 1.0,  # Check every 1 second
    ) -> ConsistencyReport:
        """
        Extract frames and use Gemini to verify tracking targets persist.
        """
        frames = await self._extract_frames(video_bytes, sample_interval)
        
        consistency_scores = []
        for i, frame in enumerate(frames):
            # Use Gemini Vision to check if targets are present
            score = await self._evaluate_frame_consistency(
                frame,
                tracking_targets,
                reference_frame=frames[0],
            )
            consistency_scores.append(score)
        
        return ConsistencyReport(
            overall_score=sum(consistency_scores) / len(consistency_scores),
            frame_scores=consistency_scores,
            drift_detected=any(s < 0.7 for s in consistency_scores),
        )
```

### Recommendation B: Physics-Aware Motion Guidelines

**Concept**: Embed physics constraints in prompt templates.

**Update to Tool Templates**:

```python
# New placeholder in video_prompt_template
"{physics_constraints}"

# Filled at runtime based on scene type
physics_constraints_mapping = {
    "vehicle": """
        Physics Constraints:
        - Maintain consistent velocity vector throughout transformation
        - Acceleration/deceleration must follow realistic curves
        - No sudden teleportation or discontinuous motion
        - Wheels maintain ground contact unless intentionally airborne
        - Body deformation follows fluid dynamics (for morphing)
    """,
    "human": """
        Physics Constraints:
        - Feet maintain grounded weight on terrain
        - Hair/clothing follows gravity unless wind is specified
        - No sliding or floating movement
        - Body proportions remain consistent
    """,
    # ... more scene types
}
```

### Recommendation C: Enhanced Subject Referencing (Already Have pgvector)

**Current State**: RABA has pgvector in Supabase for RAG, but it's underutilized for visual consistency.

**Enhancement**:

```python
class SubjectReferenceService:
    """
    Store and retrieve visual embeddings for subject consistency.
    Uses existing pgvector infrastructure.
    """
    
    async def store_subject_embedding(
        self,
        subject_id: str,
        image_bytes: bytes,
        metadata: dict,
    ) -> str:
        """Generate and store embedding for a subject's visual appearance."""
        # Use Gemini to generate description + embedding
        embedding = await self.gemini.generate_embedding(
            image_bytes,
            model="text-embedding-004"
        )
        
        await self.supabase.table("subject_embeddings").insert({
            "subject_id": subject_id,
            "embedding": embedding,
            "metadata": metadata,
        }).execute()
    
    async def get_similar_references(
        self,
        subject_description: str,
        limit: int = 5,
    ) -> list[str]:
        """Find visually similar reference images for consistency."""
        query_embedding = await self.gemini.generate_embedding(subject_description)
        
        results = await self.supabase.rpc(
            "match_subject_embeddings",
            {"query_embedding": query_embedding, "match_count": limit}
        ).execute()
        
        return [r["image_url"] for r in results.data]
```

**Files to Create**:
- `app/services/temporal_tracking.py`
- `app/services/subject_reference.py`
- `app/tools/specialized/physics_aware.py`

**Implementation Effort**: High (3-4 weeks for all three)

---

## Issue 5: Audio-Visual Synchronization

### Critique
> "The powerful narrative script requires precise timing. Ensure native joint processing with Veo 3.1 and multi-layer audio strategy."

### Current RABA Implementation

**Location**: `app/agents/video_generator.py:311-338` - Audio Block

```python
# Current audio handling
if enable_audio and segment_ctx:
    parts.append("[AUDIO]\n")
    if dlg:
        parts.append(f'Dialogue: "{dlg}"\n')
    if sfx:
        parts.append(f"SFX: {sfx}\n")
    if amb:
        parts.append(f"Ambient: {amb}\n")
    if mus:
        parts.append(f"Music: {mus}\n")
```

**Problem**: Audio cues are passed as text instructions. No explicit timestamp anchoring for SFX to visual events.

### Recommendation: Event-Anchored Audio

**Enhanced Audio Block**:

```python
class EventAnchoredAudio:
    """Tie audio events to visual events rather than absolute timestamps."""
    
    def build_audio_block(
        self,
        segment_ctx: dict,
        script_output: dict,
    ) -> str:
        """
        Build audio block with event anchors instead of timestamps.
        
        Instead of: "Bass drop at 3.2s"
        Use: "Bass drop WHEN the Roadster begins morphing"
        """
        audio_block = "[AUDIO - EVENT ANCHORED]\n"
        
        # Dialogue tied to visual action
        if segment_ctx.get("dialogue_cue"):
            visual_anchor = segment_ctx.get("segment_action", "scene begins")
            audio_block += f'Dialogue: "{segment_ctx["dialogue_cue"]}" '
            audio_block += f'(spoken DURING: {visual_anchor})\n'
        
        # SFX tied to visual events
        if segment_ctx.get("sfx_cue"):
            trigger_event = self._extract_trigger_event(segment_ctx)
            audio_block += f'SFX: {segment_ctx["sfx_cue"]} '
            audio_block += f'(triggered BY: {trigger_event})\n'
        
        # Ambient continuous
        if segment_ctx.get("ambient_cue"):
            audio_block += f'Ambient: {segment_ctx["ambient_cue"]} (continuous)\n'
        
        # Music with intensity mapping
        if segment_ctx.get("music_cue"):
            intensity_map = self._build_intensity_map(script_output)
            audio_block += f'Music: {segment_ctx["music_cue"]}\n'
            audio_block += f'Intensity Map: {intensity_map}\n'
        
        return audio_block
```

**Multi-Layer Audio Strategy in Tool Templates**:

Update `video_prompt_template` requirements in `tool_enhancer.py`:

```markdown
**CRITICAL: MULTI-LAYER AUDIO STRATEGY**
Templates MUST instruct layered audio design:
1. **Dialogue Layer**: Voice-over synced to visual action (not timestamps)
2. **SFX Layer**: Sound effects tied to visual EVENTS (e.g., "metallic clang ON collision")
3. **Ambient Layer**: Continuous environmental soundscape
4. **Music Layer**: Intensity-mapped to visual pacing
```

**Implementation Effort**: Low-Medium (3-5 days)

---

## Implementation Roadmap

### Phase 1: Quick Wins (Week 1)
| Task | Impact | Effort | Priority |
|------|--------|--------|----------|
| Tool template instruction-following placeholders | High | Low | **P0** |
| Event-anchored audio block | Medium | Low | P1 |
| Text overlay post-processing service | High | Medium | **P0** |

### Phase 2: Core Improvements (Weeks 2-3)
| Task | Impact | Effort | Priority |
|------|--------|--------|----------|
| Compositional Scene Parser (CSP) | High | Medium | **P0** |
| Temporal Consistency Manager | High | Medium | P1 |
| Physics-aware prompt constraints | Medium | Low | P1 |

### Phase 3: Advanced Features (Weeks 4-6)
| Task | Impact | Effort | Priority |
|------|--------|--------|----------|
| Progressive Video Refinement (PVR) | Very High | High | P1 |
| Temporal Tracking Tool (Gemini-based) | Medium | Medium | P2 |
| Subject Reference Service (pgvector) | Medium | Medium | P2 |

---

## Mapping to Current RABA Files

| Component | Current File | Proposed Changes |
|-----------|--------------|------------------|
| Workflow Orchestration | `app/graph/workflow.py` | Add PVR conditional nodes |
| Scene Parsing | (new) | Create `app/services/scene_parser.py` |
| Temporal Tracking | (new) | Create `app/services/temporal_tracking.py` |
| Text Overlays | (new) | Create `app/services/text_overlay.py` |
| Audio Block | `app/agents/video_generator.py:311-338` | Add event anchoring |
| Tool Templates | `app/services/tool_enhancer.py` | Add instruction placeholders |
| Subject Reference | (new) | Create `app/services/subject_reference.py` |
| Physics Constraints | `app/models/tool.py` | Add physics_constraints field |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| PVR increases generation time significantly | High | Medium | Offer PVR as opt-in for "complex" videos |
| Veo API doesn't support event-anchored audio | Medium | Low | Fall back to timestamp-based |
| Text overlay FFmpeg dependency | Low | Low | Already have FFmpeg for trimming |
| pgvector subject matching is slow | Low | Medium | Cache embeddings in Redis |

---

## Critical: Tool Creation/Enhancer is Source of Truth

**IMPORTANT**: All prompt template changes MUST be reflected in `app/services/tool_enhancer.py`:

- **`TOOL_ENHANCEMENT_SYSTEM_PROMPT`** - Controls new tool creation
- **`TOOL_IMPROVEMENT_SYSTEM_PROMPT`** - Controls tool improvement/bulk updates

The tools store `script_prompt_template`, `image_prompt_template`, and `video_prompt_template` in the database. These templates are generated by the tool enhancer and used by the script_writer, image_generator, and video_generator agents.

**When adding new architectural features** (CSP, PVR, etc.), you must:
1. Add new placeholders to tool_enhancer prompts
2. Update agents to fill those placeholders at runtime
3. Bulk-improve existing tools to regenerate their templates

---

## Conclusion

The critique accurately identifies RABA's current limitations for complex temporal transformations. The recommended improvements fall into three categories:

1. **Immediate fixes** (instruction-following, text overlays) - Can be implemented this week
2. **Core improvements** (CSP, temporal consistency) - 2-3 weeks of work
3. **Advanced features** (PVR, tracking) - Longer-term roadmap items

The key insight is that RABA's linear workflow is sufficient for simple shorts but needs compositional feedback loops for complex transformations like "liquid-morphing."

---

*Document created: January 2026*
