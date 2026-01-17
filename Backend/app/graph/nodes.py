"""RABA LangGraph Node Functions.

Node functions for each agent in the video generation workflow.
"""

from app.agents.intent_tool_selector import IntentToolSelectorAgent
from app.models.tool import ToolMetadata, ToolCapabilities
from app.models.workflow import CategoryEnum
from app.graph.state import VideoGenerationState
from app.utils.helpers import utc_now_iso
from app.utils.logging import (
    get_logger,
    log_header,
    log_subheader,
    log_key_value,
    log_success,
    log_error_msg,
    log_agent_event,
    log_workflow_event,
    log_operation,
    Colors,
)

logger = get_logger(__name__)


async def intent_tool_selector_node(state: VideoGenerationState) -> dict:
    """
    LangGraph node for Intent/Tool Selection.
    
    This is the FIRST node in the workflow. It extracts intent from the topic
    and selects the optimal video generation tool.
    
    Input from state:
        - topic: User's video topic
        - duration_seconds: Requested duration
        - aspect_ratio: Video aspect ratio
        - resolution: Video resolution
        - category: Category preference
        - user_reference_image_url: Optional user reference image
        
    Output to state:
        - intent_metadata: Extracted intent information
        - selected_tool: Selected tool metadata
        - tool_execution_params: Tool-specific parameters
        
    Args:
        state: Current workflow state
        
    Returns:
        State update dict with intent/tool selection results
    """
    workflow_id = state.get("workflow_id", "unknown")
    topic = state.get("topic", "")
    
    log_header(logger, f"AGENT: Intent/Tool Selector")
    log_agent_event(logger, "IntentToolSelector", "Starting", workflow_id)
    log_key_value(logger, "Topic", topic[:60] + "..." if len(topic) > 60 else topic)
    
    try:
        # Build tool list honoring user overrides
        tools_metadata: list[ToolMetadata] = []
        try:
            from app.tools.registry import get_tool_registry
            registry = get_tool_registry()
            user_tool_id = state.get("user_selected_tool_id")
            category_value = state.get("category", "auto") or "auto"
            forced_category = None
            try:
                if category_value != "auto":
                    forced_category = CategoryEnum(category_value)
            except Exception:
                forced_category = None

            if user_tool_id:
                # Enforce specific tool
                tool = await registry.get_by_tool_id(user_tool_id)
                if not tool:
                    raise ValueError(f"User-selected tool not found: {user_tool_id}")
                # Map ToolResponse -> ToolMetadata
                tm = ToolMetadata(
                    tool_id=tool.tool_id,
                    tool_name=tool.tool_name,
                    category=CategoryEnum(tool.category),
                    description=tool.description or "",
                    capabilities=ToolCapabilities(**(tool.capabilities or {})),
                    supported_aspect_ratios=["9:16", "16:9"],
                    supported_resolutions=["720p", "1080p"],
                    max_duration_seconds=60,
                    cost_per_request=0.5,
                    estimated_quality=0.8,
                    video_prompt_template=tool.video_prompt_template,
                    image_prompt_template=tool.image_prompt_template,
                    example_topics=[],
                )
                tools_metadata = [tm]
            else:
                # Filter by category if provided (not auto)
                list_result = await registry.list_tools(
                    category=forced_category.value if forced_category else None,
                    is_active=True,
                    limit=100,
                    offset=0,
                )
                for tr in list_result.tools:
                    tm = ToolMetadata(
                        tool_id=tr.tool_id,
                        tool_name=tr.tool_name,
                        category=CategoryEnum(tr.category),
                        description=tr.description or "",
                        capabilities=ToolCapabilities(**(tr.capabilities or {})),
                        supported_aspect_ratios=["9:16", "16:9"],
                        supported_resolutions=["720p", "1080p"],
                        max_duration_seconds=60,
                        cost_per_request=0.5,
                        estimated_quality=0.8,
                        video_prompt_template=tr.video_prompt_template,
                        image_prompt_template=tr.image_prompt_template,
                        example_topics=[],
                    )
                    tools_metadata.append(tm)
        except Exception as reg_err:
            logger.warning(f"Tool registry unavailable or failed to load tools: {reg_err}. Falling back to default tools.")
            tools_metadata = None  # type: ignore[assignment]

        agent = IntentToolSelectorAgent(tools=tools_metadata)
        
        result = await agent.run(
            topic=topic,
            duration_seconds=state.get("duration_seconds", 18),
            aspect_ratio=state.get("aspect_ratio", "9:16"),
            resolution=state.get("resolution", "1080p"),
            category=state.get("category", "auto"),
            user_has_reference_image=bool(state.get("user_reference_image_url")),
        )
        
        log_success(logger, f"Intent extracted: {result.intent_metadata.intent_type.value}")
        log_key_value(logger, "Tool selected", result.selected_tool.tool_name)
        log_key_value(logger, "Confidence", f"{result.confidence:.2f}")
        
        # Build tool_selection object for database persistence
        tool_selection_data = {
            "selected_tool": result.selected_tool.model_dump(),
            "intent_metadata": result.intent_metadata.model_dump(),
            "validated_params": result.validated_params.model_dump(),
            "tool_execution_params": result.tool_execution_params,
            "confidence": result.confidence,
            "fallback_used": result.fallback_used,
            "selection_reasoning": result.selection_reasoning,
        }
        
        state_update = {
            "intent_metadata": result.intent_metadata.model_dump(),
            "selected_tool": result.selected_tool.model_dump(),
            "tool_execution_params": result.tool_execution_params,
            "tool_selection": tool_selection_data,  # Add for database persistence
            "phase_timestamps": {
                **state.get("phase_timestamps", {}),
                "intent_tool_completed": utc_now_iso(),
            },
        }
        
        # Persist tool_selection to database
        try:
            from app.services.supabase import get_workflow_repository
            repo = get_workflow_repository()
            await repo.update(workflow_id, {
                "tool_selection": tool_selection_data,
                "updated_at": utc_now_iso(),
            })
            logger.info(f"Persisted tool_selection to database for workflow {workflow_id}")
        except Exception as e:
            log_warning_msg(logger, f"Failed to persist tool_selection: {e}")
        
        log_agent_event(logger, "IntentToolSelector", "Completed", workflow_id)
        
        return state_update
        
    except Exception as e:
        log_error_msg(logger, f"Intent/Tool Selection failed: {e}")
        
        return {
            "error": f"Intent/Tool Selection failed: {str(e)}",
            "error_details": {
                "node": "intent_tool_selector",
                "exception": str(e),
                "timestamp": utc_now_iso(),
            },
            "phase_timestamps": {
                **state.get("phase_timestamps", {}),
                "intent_tool_failed": utc_now_iso(),
            },
        }


async def deep_research_node(state: VideoGenerationState) -> dict:
    """
    LangGraph node for Deep Research.
    
    Routes between factual, creative, and hybrid research strategies based on
    content type determined from intent_type and topic analysis.
    
    Input from state:
        - topic: User's video topic
        - intent_metadata: From Intent/Tool Selector (includes intent_type, tone)
        - selected_tool: Selected tool with category
        - duration_seconds: Video duration
        - workflow_id: For storage organization
        
    Output to state:
        - research_data: Research output (factual, creative, or hybrid)
        - research_images: List of image URLs from search
        
    Reference: PHASE2_3_DEEP_RESEARCH_PLAN.md
    """
    workflow_id = state.get("workflow_id", "unknown")
    topic = state.get("topic", "")
    
    log_header(logger, f"AGENT: Deep Research")
    log_agent_event(logger, "DeepResearch", "Starting", workflow_id)
    log_key_value(logger, "Topic", topic[:60] + "..." if len(topic) > 60 else topic)
    
    try:
        from app.agents.deep_research import get_deep_research_agent
        agent = get_deep_research_agent()
        updated_state = await agent.research(state)
        
        research_data = updated_state.get("research_data", {})
        research_images = updated_state.get("research_images", [])
        strategy = research_data.get("strategy_used", "unknown")
        
        log_success(logger, f"Research completed with strategy: {strategy}")
        log_key_value(logger, "Images found", len(research_images))
        log_key_value(logger, "Is fictional", research_data.get('is_fictional', False))
        
        # Detailed logging of research output quality
        findings = research_data.get("research_findings", [])
        visual_elements = research_data.get("visual_elements", [])
        interesting_angles = research_data.get("interesting_angles", [])
        exec_summary = research_data.get("executive_summary", "")
        
        logger.info(f"[RESEARCH OUTPUT] Executive summary length: {len(exec_summary)} chars")
        logger.info(f"[RESEARCH OUTPUT] Research findings count: {len(findings)}")
        for i, finding in enumerate(findings[:3], 1):
            if isinstance(finding, dict):
                segment = finding.get("topic_segment", "Unknown")
                facts_count = len(finding.get("key_facts", []))
                confidence = finding.get("confidence", 0)
                logger.info(f"[RESEARCH OUTPUT] Finding {i}: {segment} ({facts_count} facts, conf: {confidence})")
        logger.info(f"[RESEARCH OUTPUT] Visual elements count: {len(visual_elements)}")
        if visual_elements:
            logger.info(f"[RESEARCH OUTPUT] Visual elements: {visual_elements[:2]}...")
        logger.info(f"[RESEARCH OUTPUT] Interesting angles count: {len(interesting_angles)}")
        if interesting_angles:
            logger.info(f"[RESEARCH OUTPUT] Angles: {interesting_angles[:2]}...")
        logger.info(f"[RESEARCH OUTPUT] Research images: {len(research_images)}")
        
        state_update = {
            "research_data": research_data,
            "research_images": research_images,
            "phase_timestamps": {
                **state.get("phase_timestamps", {}),
                "deep_research_completed": utc_now_iso(),
            },
        }
        
        log_agent_event(logger, "DeepResearch", "Completed", workflow_id)
        
        return state_update
        
    except Exception as e:
        log_error_msg(logger, f"Deep Research failed: {e}")
        
        return {
            "error": f"Deep Research failed: {str(e)}",
            "error_details": {
                "node": "deep_research",
                "exception": str(e),
                "timestamp": utc_now_iso(),
            },
            "phase_timestamps": {
                **state.get("phase_timestamps", {}),
                "deep_research_failed": utc_now_iso(),
            },
        }


async def script_writer_node(state: VideoGenerationState) -> dict:
    """
    LangGraph node for Script Writer.
    
    Generates a viral-optimized script from research data using the selected
    tool's style specifications.
    
    Input from state:
        - topic: User's video topic
        - research_data: From Deep Research (factual/creative/hybrid)
        - selected_tool: Tool metadata with style specs
        - intent_metadata: Intent type, tone, target audience
        - duration_seconds: Video duration
        
    Output to state:
        - script_output: Complete script as dict
        - hook: Hook section extracted
        - scenes: List of scenes extracted
        - call_to_action: CTA section extracted
        - viral_score: Calculated viral score
        
    Reference: PHASE2_4_SCRIPT_GENERATOR_PLAN.md
    """
    workflow_id = state.get("workflow_id", "unknown")
    topic = state.get("topic", "")
    duration = state.get("duration_seconds", 18)
    research_data = state.get("research_data", {})
    
    log_header(logger, f"AGENT: Script Writer")
    log_agent_event(logger, "ScriptWriter", "Starting", workflow_id)
    log_key_value(logger, "Topic", topic[:60] + "..." if len(topic) > 60 else topic)
    log_key_value(logger, "Target duration", f"{duration}s")
    
    # Log input data for debugging
    logger.info(f"[SCRIPT INPUT] Research data keys: {list(research_data.keys()) if research_data else 'None'}")
    findings_count = len(research_data.get("research_findings", []))
    logger.info(f"[SCRIPT INPUT] Research findings count: {findings_count}")
    
    try:
        from app.agents.script_writer import get_script_writer_agent
        
        agent = get_script_writer_agent()
        result = await agent.run(state)
        
        script_output = result.get("script_output", {})
        viral_score = result.get("viral_score", 0.0)
        scenes = result.get("scenes", [])
        scenes_count = len(scenes)
        hook = result.get("hook", {})
        cta = result.get("call_to_action", {})
        
        log_success(logger, "Script generated successfully")
        log_key_value(logger, "Viral score", f"{viral_score:.2f}")
        log_key_value(logger, "Scenes", scenes_count)
        
        # Detailed script logging
        logger.info(f"[SCRIPT OUTPUT] Hook: {hook.get('script', 'N/A')[:100]}")
        for i, scene in enumerate(scenes[:3], 1):  # Log first 3 scenes
            logger.info(f"[SCRIPT OUTPUT] Scene {i}: {scene.get('description', 'N/A')[:80]}...")
        logger.info(f"[SCRIPT OUTPUT] CTA: {cta.get('script', 'N/A')[:80]}")
        logger.info(f"[SCRIPT OUTPUT] Script saved to state: {bool(script_output)}")
        
        # Persist script_output to database
        try:
            from app.services.supabase import get_supabase_service
            import json
            from datetime import datetime
            
            # Helper to serialize datetime objects
            def json_serializer(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
            
            # Convert to JSON-safe dict by serializing and deserializing
            script_output_safe = json.loads(json.dumps(script_output, default=json_serializer))
            
            supabase = get_supabase_service()
            await supabase.update_workflow(
                workflow_id=workflow_id,
                updates={
                    "script_output": script_output_safe,
                    "status": "script_complete",
                },
            )
            logger.info(f"[SCRIPT OUTPUT] Persisted to database: {workflow_id}")
        except Exception as db_error:
            logger.error(f"[SCRIPT OUTPUT] Database persistence failed: {db_error}")
        
        state_update = {
            "script_output": script_output,
            "hook": hook,
            "scenes": scenes,
            "call_to_action": cta,
            "viral_score": viral_score,
            "phase_timestamps": {
                **state.get("phase_timestamps", {}),
                "script_writer_completed": utc_now_iso(),
            },
        }
        
        log_agent_event(logger, "ScriptWriter", "Completed", workflow_id)
        
        return state_update
        
    except Exception as e:
        log_error_msg(logger, f"Script Writer failed: {e}")
        
        return {
            "error": f"Script Writer failed: {str(e)}",
            "error_details": {
                "node": "script_writer",
                "exception": str(e),
                "timestamp": utc_now_iso(),
            },
            "phase_timestamps": {
                **state.get("phase_timestamps", {}),
                "script_writer_failed": utc_now_iso(),
            },
        }


async def image_generator_node(state: VideoGenerationState) -> dict:
    """
    LangGraph node for Image Generator.
    
    Generates 1-5 reference images using Nano Banana Pro/Flash based on
    script scenes. Maintains visual consistency across all images.
    
    Input from state:
        - workflow_id: For storage path
        - script_output: Contains scenes[]
        - selected_tool: Tool metadata with style specs
        - user_reference_image_url: Optional user reference
        - research_images: Images from Deep Research
        - aspect_ratio, resolution: Video specs
        
    Output to state:
        - generated_images: List of generated image URLs
        - all_images: Combined list of all image URLs
        - image_metadata: Metadata for each image
        
    Reference: PHASE3_1_IMAGE_GENERATOR_PLAN.md
    """
    workflow_id = state.get("workflow_id", "unknown")
    topic = state.get("topic", "")
    
    log_header(logger, f"AGENT: Image Generator")
    log_agent_event(logger, "ImageGenerator", "Starting", workflow_id)
    log_key_value(logger, "Topic", topic[:60] + "..." if len(topic) > 60 else topic)
    
    try:
        from app.agents.image_generator import ImageGeneratorAgent
        
        agent = ImageGeneratorAgent()
        result = await agent.run(state)
        
        if result.get("error"):
            logger.error(f"Image generation error: {result.get('error')}")
            return result
        
        generated_count = len(result.get("generated_images", []))
        all_count = len(result.get("all_images", []))
        
        log_success(logger, f"Generated {generated_count} images")
        log_key_value(logger, "Total images (incl. external)", all_count)
        
        # Extract image URLs for database persistence
        generated_image_urls = result.get("generated_images", [])
        if isinstance(generated_image_urls, list):
            # Extract URLs if they're objects
            image_urls = []
            for img in generated_image_urls:
                if isinstance(img, str):
                    image_urls.append(img)
                elif isinstance(img, dict):
                    url = img.get("url") or img.get("image_url") or img.get("storage_url")
                    if url:
                        image_urls.append(url)
            generated_image_urls = image_urls
        
        state_update = {
            "generated_images": result.get("generated_images", []),
            "all_images": result.get("all_images", []),
            "image_metadata": result.get("image_metadata", []),
            "phase_timestamps": {
                **state.get("phase_timestamps", {}),
                "image_generator_completed": utc_now_iso(),
            },
        }
        
        # Persist generated_images to database
        try:
            from app.services.supabase import get_workflow_repository
            repo = get_workflow_repository()
            await repo.update(workflow_id, {
                "generated_images": generated_image_urls,  # Store as array of URLs
                "updated_at": utc_now_iso(),
            })
            logger.info(f"Persisted {len(generated_image_urls)} generated images to database for workflow {workflow_id}")
        except Exception as e:
            log_warning_msg(logger, f"Failed to persist generated_images: {e}")
        
        log_agent_event(logger, "ImageGenerator", "Completed", workflow_id)
        
        return state_update
        
    except Exception as e:
        log_error_msg(logger, f"Image Generator failed: {e}")
        
        return {
            "error": f"Image Generator failed: {str(e)}",
            "error_details": {
                "node": "image_generator",
                "exception": str(e),
                "timestamp": utc_now_iso(),
            },
            "phase_timestamps": {
                **state.get("phase_timestamps", {}),
                "image_generator_failed": utc_now_iso(),
            },
        }


async def video_generator_node(state: VideoGenerationState) -> dict:
    """
    LangGraph node for Video Generator.
    
    Generates final YouTube Shorts (8-25 seconds) using Veo 3.1 with native
    audio from script, reference images, and workflow state.
    
    Input from state:
        - workflow_id: For storage path
        - script_output: Contains hook, scenes, CTA
        - generated_images: From Image Generator (max 3)
        - user_reference_image_url: Optional user reference
        - research_images: Images from Deep Research
        - selected_tool: Tool metadata with style specs
        - duration_seconds: Target video duration (8-25s)
        - aspect_ratio, resolution: Video specs
        - enable_audio: Whether to generate native audio
        
    Output to state:
        - video_output: Complete video metadata
        - final_video_url: Public URL of final video
        - video_metadata: Duration, segments, quality info
        
    Reference: PHASE3_2_VIDEO_GENERATOR_PLAN.md
    """
    workflow_id = state.get("workflow_id", "unknown")
    topic = state.get("topic", "")
    duration = state.get("duration_seconds", 18)
    
    log_header(logger, f"AGENT: Video Generator")
    log_agent_event(logger, "VideoGenerator", "Starting", workflow_id)
    log_key_value(logger, "Topic", topic[:60] + "..." if len(topic) > 60 else topic)
    log_key_value(logger, "Target duration", f"{duration}s")
    
    # Detailed logging of inputs passed to Video Generator
    script_output = state.get("script_output", {})
    generated_images = state.get("generated_images", [])
    research_images = state.get("research_images", [])
    scenes = state.get("scenes", [])
    hook = state.get("hook", {})
    
    logger.info(f"[VIDEO INPUT] Script output present: {bool(script_output)}")
    logger.info(f"[VIDEO INPUT] Hook: {hook.get('script', 'N/A')[:60] if hook else 'None'}")
    logger.info(f"[VIDEO INPUT] Scenes count: {len(scenes)}")
    for i, scene in enumerate(scenes[:3], 1):
        logger.info(f"[VIDEO INPUT] Scene {i} description: {scene.get('description', 'N/A')[:60]}...")
    logger.info(f"[VIDEO INPUT] Generated images (Nano Banana): {len(generated_images) if generated_images else 0}")
    if generated_images:
        for i, img_url in enumerate(generated_images[:3], 1):
            logger.info(f"[VIDEO INPUT] Gen Image {i}: {img_url[:80]}...")
    logger.info(f"[VIDEO INPUT] Research images (reference only): {len(research_images) if research_images else 0}")
    
    try:
        from app.agents.video_generator import VideoGeneratorAgent
        
        agent = VideoGeneratorAgent()
        result = await agent.run(state)
        
        if result.get("error"):
            logger.error(f"Video generation error: {result.get('error')}")
            return result
        
        video_url = result.get("final_video_url", "")
        video_metadata = result.get("video_metadata", {})
        segments = video_metadata.get("segments", 1)
        
        log_success(logger, f"Video generated successfully")
        log_key_value(logger, "Video URL", video_url[:60] + "..." if len(video_url) > 60 else video_url)
        log_key_value(logger, "Segments", segments)
        
        state_update = {
            "video_output": result.get("video_output"),
            "final_video_url": video_url,
            "video_metadata": video_metadata,
            "phase_timestamps": {
                **state.get("phase_timestamps", {}),
                "video_generator_completed": utc_now_iso(),
            },
        }
        
        log_agent_event(logger, "VideoGenerator", "Completed", workflow_id)
        
        return state_update
        
    except Exception as e:
        log_error_msg(logger, f"Video Generator failed: {e}")
        
        return {
            "error": f"Video Generator failed: {str(e)}",
            "error_details": {
                "node": "video_generator",
                "exception": str(e),
                "timestamp": utc_now_iso(),
            },
            "phase_timestamps": {
                **state.get("phase_timestamps", {}),
                "video_generator_failed": utc_now_iso(),
            },
        }


async def output_processor_node(state: VideoGenerationState) -> dict:
    """
    LangGraph node for Output Processing.
    
    Finalizes the workflow after video generation completes.
    NOT a separate agent - a post-processing workflow step.
    
    Input from state:
        - workflow_id
        - video_output (from Video Generator)
        - final_video_url
        - generated_images, all_images
        - script_output, research_data
        - selected_tool
        - phase_timestamps, started_at
        
    Output to state:
        - status: "completed" or "failed"
        - completed_at: timestamp
        - generation_time_seconds: total time
        - final_output: complete response object
        
    Reference: RABA_Architecture.md Section 2.8, PHASE3_3_OUTPUT_PROCESSOR_PLAN.md
    """
    workflow_id = state.get("workflow_id", "unknown")
    
    log_header(logger, f"OUTPUT PROCESSOR")
    log_workflow_event(logger, workflow_id, "Finalizing workflow")
    
    try:
        from app.services.workflow_service import get_workflow_service
        
        service = get_workflow_service()
        
        is_valid, error_msg = service.validate_completion_ready(state)
        
        if not is_valid:
            logger.error(f"Workflow not ready for completion: {error_msg}")
            
            error_output = service.build_error_output(state)
            
            await service.update_workflow_failed(
                workflow_id=workflow_id,
                error=error_msg,
                error_details={"phase": "output_processor", "validation_failed": True},
            )
            
            return {
                "status": "failed",
                "error": error_msg,
                "final_output": error_output.to_api_response(),
                "completed_at": utc_now_iso(),
                "phase_timestamps": {
                    **state.get("phase_timestamps", {}),
                    "output_processor_failed": utc_now_iso(),
                },
            }
        
        completion_output = service.build_completion_output(state)
        
        await service.update_workflow_completed(
            workflow_id=workflow_id,
            output=completion_output,
        )
        
        final_response = completion_output.to_api_response()
        
        log_success(logger, "Workflow completed successfully!")
        log_key_value(logger, "Total generation time", completion_output.timing.formatted_total)
        log_key_value(logger, "Video URL", completion_output.video.url[:60] + "..." if len(completion_output.video.url) > 60 else completion_output.video.url)
        log_key_value(logger, "Images", completion_output.images.total_count)
        
        state_update = {
            "status": "completed",
            "completed_at": utc_now_iso(),
            "generation_time_seconds": completion_output.timing.total_seconds,
            "final_output": final_response,
            "phase_timestamps": {
                **state.get("phase_timestamps", {}),
                "output_processor_completed": utc_now_iso(),
            },
        }
        
        log_workflow_event(logger, workflow_id, "Output processing completed")
        
        return state_update
        
    except Exception as e:
        log_error_msg(logger, f"Output Processor failed: {e}")
        
        return {
            "status": "failed",
            "error": f"Output processing failed: {str(e)}",
            "error_details": {
                "node": "output_processor",
                "exception": str(e),
                "timestamp": utc_now_iso(),
            },
            "completed_at": utc_now_iso(),
            "phase_timestamps": {
                **state.get("phase_timestamps", {}),
                "output_processor_failed": utc_now_iso(),
            },
        }


async def error_handler_node(state: VideoGenerationState) -> dict:
    """
    LangGraph node for Error Handling.
    
    Handles errors from any node and prepares error response.
    """
    logger.error("NODE: Error Handler - Processing error")
    logger.error(f"Error: {state.get('error')}")
    
    return {
        "phase_timestamps": {
            **state.get("phase_timestamps", {}),
            "error_handled": utc_now_iso(),
        },
        "completed_at": utc_now_iso(),
    }


async def hitl_tool_gate_node(state: VideoGenerationState) -> dict:
    """HITL gate after tool selection - pauses for user approval.
    
    Stores tool selection output and updates workflow status to awaiting approval.
    Reference: SRS.md FR-702, FR-706, FR-707
    """
    from app.models.hitl import HITLGate
    from app.services.hitl_service import get_hitl_service
    
    logger.info("NODE: HITL Tool Gate - Pausing for approval")
    
    workflow_id = state.get("workflow_id")
    gate = HITLGate.TOOL_SELECTION
    
    # Collect output for user review
    current_output = {
        "selected_tool": state.get("selected_tool"),
        "intent_metadata": state.get("intent_metadata"),
        "tool_execution_params": state.get("tool_execution_params"),
    }
    
    # Pause workflow via service
    service = get_hitl_service()
    await service.pause_at_gate(workflow_id, gate, current_output)
    
    return {
        "current_hitl_gate": gate.value,
        "hitl_gate_outputs": {gate.value: current_output},
    }


async def hitl_research_gate_node(state: VideoGenerationState) -> dict:
    """HITL gate after research - pauses for user approval.
    
    Stores research output and updates workflow status to awaiting approval.
    Reference: SRS.md FR-702, FR-706, FR-707
    """
    from app.models.hitl import HITLGate
    from app.services.hitl_service import get_hitl_service
    
    logger.info("NODE: HITL Research Gate - Pausing for approval")
    
    workflow_id = state.get("workflow_id")
    gate = HITLGate.RESEARCH
    
    current_output = {
        "research_output": state.get("research_output"),
        "research_images": state.get("research_images"),
    }
    
    service = get_hitl_service()
    await service.pause_at_gate(workflow_id, gate, current_output)
    
    return {
        "current_hitl_gate": gate.value,
        "hitl_gate_outputs": {gate.value: current_output},
    }


async def hitl_script_gate_node(state: VideoGenerationState) -> dict:
    """HITL gate after script - pauses for user approval.
    
    Stores script output and updates workflow status to awaiting approval.
    Reference: SRS.md FR-702, FR-706, FR-707
    """
    from app.models.hitl import HITLGate
    from app.services.hitl_service import get_hitl_service
    
    logger.info("NODE: HITL Script Gate - Pausing for approval")
    
    workflow_id = state.get("workflow_id")
    gate = HITLGate.SCRIPT
    
    current_output = {
        "script_output": state.get("script_output"),
    }
    
    service = get_hitl_service()
    await service.pause_at_gate(workflow_id, gate, current_output)
    
    return {
        "current_hitl_gate": gate.value,
        "hitl_gate_outputs": {gate.value: current_output},
    }


async def hitl_image_gate_node(state: VideoGenerationState) -> dict:
    """HITL gate after images - pauses for user approval.
    
    Stores generated images and updates workflow status to awaiting approval.
    Reference: SRS.md FR-702, FR-706, FR-707
    """
    from app.models.hitl import HITLGate
    from app.services.hitl_service import get_hitl_service
    
    logger.info("NODE: HITL Image Gate - Pausing for approval")
    
    workflow_id = state.get("workflow_id")
    gate = HITLGate.IMAGES
    
    current_output = {
        "generated_images": state.get("generated_images"),
        "image_metadata": state.get("image_metadata"),
    }
    
    service = get_hitl_service()
    await service.pause_at_gate(workflow_id, gate, current_output)
    
    return {
        "current_hitl_gate": gate.value,
        "hitl_gate_outputs": {gate.value: current_output},
    }


async def hitl_video_gate_node(state: VideoGenerationState) -> dict:
    """HITL gate after video - pauses for user approval.
    
    Stores video output and updates workflow status to awaiting approval.
    Reference: SRS.md FR-702, FR-706, FR-707
    """
    from app.models.hitl import HITLGate
    from app.services.hitl_service import get_hitl_service
    
    logger.info("NODE: HITL Video Gate - Pausing for approval")
    
    workflow_id = state.get("workflow_id")
    gate = HITLGate.VIDEO
    
    current_output = {
        "video_output": state.get("video_output"),
        "final_video_url": state.get("final_video_url"),
    }
    
    service = get_hitl_service()
    await service.pause_at_gate(workflow_id, gate, current_output)
    
    return {
        "current_hitl_gate": gate.value,
        "hitl_gate_outputs": {gate.value: current_output},
    }
