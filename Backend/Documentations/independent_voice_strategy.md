# Independent Voice Generation: Mini-SRS & Implementation Plan

**Objective:** Implement an "Audio-First" video generation pipeline where high-quality Gemini TTS drives the video timing, ensuring character consistency and precise alignment.

---

## 1. System Requirements Specification (SRS)

### 1.1 Architecture: "Audio-First" Pipeline
The system shall prioritize audio generation when `enable_audio=True`.
*   **Trigger:** User request with `enable_audio: bool = True`.
*   **Workflow:** Script -> **Voice Generation** -> **Video Generation (Constrained)** -> **Sync**.
*   **Fallback:** If `enable_audio=False`, the system utilizes the existing Video-First estimation logic.

### 1.2 Data Models
New Pydantic models required to support the pipeline.

#### A. AudioManifest
Tracks the generated audio assets and their precise timing.
```python
class AudioSegment(BaseModel):
    segment_id: int # Matches VideoSegment.segment_number
    character_name: str
    text_transcript: str
    audio_file_path: str # Local or S3 path
    duration_seconds: float # Precise duration (e.g., 4.125s)
    voice_config_used: dict # Metadata for reproducibility

class AudioManifest(BaseModel):
    segments: List[AudioSegment]
    total_duration: float
    is_generated: bool = True
```

#### B. VoiceProfile
Mapping for character consistency.
```python
class VoiceProfile(BaseModel):
    character_name: str # e.g., "Dr. Anya"
    voice_name: str # Gemini TTS voice, e.g., "Fenrir"
    gender: str
    style_preset: str # Default style instructions
```

### 1.3 Agent Specifications

#### A. VoiceGeneratorAgent (New)
*   **Role:** Generate high-fidelity TTS audio before video generation.
*   **Input:** `ScriptOutput` (from Script Agent).
*   **Logic:**
    1.  Parse Script for dialogue and character names.
    2.  Map Characters to `VoiceProfile` (using a default map or user input).
    3.  For each scene/segment:
        *   Construct TTS prompt with "Director's Notes" (Mood/Tone from Script).
        *   Call Gemini TTS API (`models.generate_content`).
        *   Save audio file.
        *   Measure exact duration.
*   **Output:** `AudioManifest`.

#### B. VideoGeneratorAgent (Update)
*   **Role:** Generate video segments constrained by audio duration.
*   **Logic:**
    1.  Check input for `AudioManifest`.
    2.  **IF Present:**
        *   Set `segment_duration` = `AudioSegment.duration_seconds`.
        *   Add `Dialogue: "..."` to Veo prompt (for visual lip movement).
    3.  **IF Absent:**
        *   Use existing logic (`estimated_duration`).

---

## 2. Files Reference

### 2.1 New Files
*   `Backend/app/agents/voice_generator.py`: Core logic for the new agent.
*   `Backend/app/models/audio.py`: Definitions for `AudioManifest`, `AudioSegment`, `VoiceProfile`.
*   `Backend/app/services/gemini_tts.py`: Wrapper service for Gemini TTS API interactions (clean separation).

### 2.2 Modified Files
*   `Backend/app/models/video.py`: Update `VideoGenerationRequest` to optionally include `AudioManifest`.
*   `Backend/app/agents/video_generator.py`: Update `plan_video_segments` to accept strict durations from audio. Update prompt building to include dialogue text.
*   `Backend/app/graph/state.py`: Update `VideoGenerationState` to carry `audio_manifest`.
*   `Backend/app/graph/workflow.py`: Update graph edges to insert `VoiceGeneratorAgent` between Script and Video agents when audio is enabled.

---

## 3. Implementation Plan

### Phase 1: Foundation (Models & Service)
*   [x] **Task 1.1:** Create `app/models/audio.py` with `AudioManifest` and `VoiceProfile`.
*   [x] **Task 1.2:** Update `app/models/video.py` to include `audio_manifest` in `VideoGenerationRequest`.
*   [x] **Task 1.3:** Create `app/services/gemini_tts.py` implementing `generate_speech` method with `SpeechConfig` and `VoiceConfig`.
    *   *Verification:* Unit test generating a small "Hello World" wav file.

### Phase 2: Voice Agent Logic
*   [x] **Task 2.1:** Create `app/agents/voice_generator.py`.
    *   Implement `run()` method.
    *   Implement parsing of `ScriptOutput` to extract dialogue per scene.
    *   Implement loop to generate audio for each segment.
    *   *Verification:* Run Agent with a mock script, verify `AudioManifest` output and valid .wav files.

### Phase 3: Video Agent Integration
*   [x] **Task 3.1:** Update `app/agents/video_generator.py`.
    *   Modify `plan_video_segments` to use `audio_manifest` timing if available.
    *   Update `build_video_prompt` to ensure `duration` matches audio manifest strictly.
    *   *Verification:* Unit test `plan_video_segments` with and without audio manifest.

### Phase 4: Workflow Orchestration
*   [x] **Task 4.1:** Update `app/graph/state.py` to include `audio_output`.
*   [x] **Task 4.2:** Update `app/graph/workflow.py`.
    *   Add conditional edge: If `enable_audio` -> `voice_agent` -> `video_agent`.
    *   Else -> `video_agent`.

### Phase 5: End-to-End Verification
*   [ ] **Task 5.1:** Run full pipeline locally.
    *   Input: `enable_audio=True`, Topic="Cyberpunk detective".
    *   Verify: Audio files generated -> Video generated with matching duration.

---

## 4. Alignment with Existing Architecture
*   **State Management:** Uses the existing `LangGraph` state (`VideoGenerationState`).
*   **Storage:** Audio assets will be stored in Supabase Storage (like images/videos), maintaining consistency.
*   **Tooling:** Reuses `Veo` service for video, adds `GeminiTTS` service (sibling relationship).
*   **Configuration:** Controlled via `VideoGenerationConfig`, preserving backward compatibility.
