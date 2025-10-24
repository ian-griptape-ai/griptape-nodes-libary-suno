"""Suno Music Generation Node - Generate AI music with custom prompts, styles, and vocals."""

from typing import Any
import time
import requests
import json
from contextlib import suppress
import logging

from griptape_nodes.exe_types.core_types import (
    Parameter,
    ParameterMode,
)
from griptape_nodes.exe_types.node_types import DataNode, AsyncResult
from griptape_nodes.traits.options import Options
from griptape_nodes.traits.slider import Slider
from griptape_nodes.retained_mode.griptape_nodes import GriptapeNodes
from griptape.artifacts import AudioUrlArtifact, ImageUrlArtifact

logger = logging.getLogger(__name__)


class SunoGenerateMusic(DataNode):
    """Generate music using Suno AI API.
    
    Supports two modes:
    - Custom Mode: Full control over lyrics, style, and title
    - Simple Mode: Auto-generate from prompt description
    
    Each request generates exactly 2 song variations.
    """
    
    # API Configuration
    SERVICE_NAME = "Suno API"
    API_KEY_NAME = "SUNO_API_KEY"
    API_BASE_URL = "https://api.sunoapi.org/api/v1"
    
    # Polling Configuration
    POLLING_INTERVAL = 10  # seconds - recommended by API
    MAX_POLLING_ATTEMPTS = 36  # 6 minutes max (2-3 min typical)
    DEFAULT_TIMEOUT = 30  # seconds for HTTP requests
    
    # Model versions
    MODELS = ["V5", "V4_5PLUS", "V4_5", "V4", "V3_5"]
    
    # Prompt length limits by model
    PROMPT_LIMITS_CUSTOM = {
        "V3_5": 3000,
        "V4": 3000,
        "V4_5": 5000,
        "V4_5PLUS": 5000,
        "V5": 5000,
    }
    PROMPT_LIMIT_SIMPLE = 500
    
    # Style length limits by model
    STYLE_LIMITS = {
        "V3_5": 200,
        "V4": 200,
        "V4_5": 1000,
        "V4_5PLUS": 1000,
        "V5": 1000,
    }
    
    TITLE_LIMIT = 80

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.category = "music"
        self.description = "Generate music tracks using Suno AI with custom prompts, styles, and vocals"
        
        # Mode selection
        mode_param = Parameter(
            name="custom_mode",
            input_types=["bool"],
            type="bool",
            default_value=False,
            tooltip="Custom Mode: Full control over lyrics/style. Simple Mode: Auto-generate from prompt.",
            allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
            ui_options={"display_name": "Custom Mode"},
        )
        self.add_parameter(mode_param)
        
        # Model selection
        model_param = Parameter(
            name="model",
            input_types=["str"],
            type="str",
            default_value="V5",
            tooltip=[
                {"type": "text", "text": "Model version for generation:"},
                {"type": "text", "text": "• V5: Superior musical expression, faster generation"},
                {"type": "text", "text": "• V4_5PLUS: Richer sound, new creation methods, max 8 min"},
                {"type": "text", "text": "• V4_5: Superior genre blending, faster, up to 8 min"},
                {"type": "text", "text": "• V4: Best audio quality, refined structure, up to 4 min"},
                {"type": "text", "text": "• V3_5: Solid arrangements, creative diversity, up to 4 min"},
            ],
            allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
            ui_options={"display_name": "Model"},
        )
        model_param.add_trait(Options(choices=self.MODELS))
        self.add_parameter(model_param)
        
        # Prompt (different meaning in each mode)
        prompt_param = Parameter(
            name="prompt",
            input_types=["str"],
            type="str",
            default_value="",
            tooltip=[
                {"type": "text", "text": "Custom Mode: Exact lyrics to sing (required if not instrumental)"},
                {"type": "text", "text": "Simple Mode: Description of desired music (auto-generates lyrics)"},
            ],
            allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
            ui_options={
                "multiline": True,
                "placeholder_text": "Enter your lyrics or description...",
                "display_name": "Prompt / Lyrics",
            },
        )
        self.add_parameter(prompt_param)
        
        # Style (custom mode only)
        style_param = Parameter(
            name="style",
            input_types=["str"],
            type="str",
            default_value="",
            tooltip="Music style or genre (e.g., 'Classical', 'Jazz', 'Electronic'). Required in Custom Mode.",
            allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
            ui_options={
                "placeholder_text": "e.g., Classical, Jazz, Rock",
                "display_name": "Style",
                "hide": True,  # Hidden by default, shown in custom mode
            },
        )
        self.add_parameter(style_param)
        
        # Title (custom mode only)
        title_param = Parameter(
            name="title",
            input_types=["str"],
            type="str",
            default_value="",
            tooltip=f"Title of the generated music track (max {self.TITLE_LIMIT} characters). Required in Custom Mode.",
            allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
            ui_options={
                "placeholder_text": "My Amazing Song",
                "display_name": "Title",
                "hide": True,  # Hidden by default, shown in custom mode
            },
        )
        self.add_parameter(title_param)
        
        # Instrumental toggle
        instrumental_param = Parameter(
            name="instrumental",
            input_types=["bool"],
            type="bool",
            default_value=False,
            tooltip="Generate instrumental music without vocals",
            allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
            ui_options={"display_name": "Instrumental (No Vocals)"},
        )
        self.add_parameter(instrumental_param)
        
        # Advanced parameters (hidden by default)
        vocal_gender_param = Parameter(
            name="vocal_gender",
            input_types=["str"],
            type="str",
            default_value="auto",
            tooltip="Preferred vocal gender (auto, male, or female)",
            allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
            ui_options={"display_name": "Vocal Gender", "hide": True},
        )
        vocal_gender_param.add_trait(Options(choices=["auto", "m", "f"]))
        self.add_parameter(vocal_gender_param)
        
        negative_tags_param = Parameter(
            name="negative_tags",
            input_types=["str"],
            type="str",
            default_value="",
            tooltip="Music styles or traits to exclude (e.g., 'Heavy Metal, Upbeat Drums')",
            allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
            ui_options={
                "placeholder_text": "Styles to avoid...",
                "display_name": "Negative Tags",
                "hide": True,
            },
        )
        self.add_parameter(negative_tags_param)
        
        style_weight_param = Parameter(
            name="style_weight",
            input_types=["float"],
            type="float",
            default_value=0.65,
            tooltip="Weight of style guidance (0.00-1.00)",
            allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
            ui_options={"display_name": "Style Weight", "hide": True},
        )
        style_weight_param.add_trait(Slider(min_val=0.0, max_val=1.0))
        self.add_parameter(style_weight_param)
        
        weirdness_param = Parameter(
            name="weirdness_constraint",
            input_types=["float"],
            type="float",
            default_value=0.65,
            tooltip="Creative deviation/novelty (0.00-1.00)",
            allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
            ui_options={"display_name": "Weirdness", "hide": True},
        )
        weirdness_param.add_trait(Slider(min_val=0.0, max_val=1.0))
        self.add_parameter(weirdness_param)
        
        audio_weight_param = Parameter(
            name="audio_weight",
            input_types=["float"],
            type="float",
            default_value=0.65,
            tooltip="Weight of audio influence (0.00-1.00)",
            allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
            ui_options={"display_name": "Audio Weight", "hide": True},
        )
        audio_weight_param.add_trait(Slider(min_val=0.0, max_val=1.0))
        self.add_parameter(audio_weight_param)
        
        # Status output
        status_param = Parameter(
            name="status",
            output_type="str",
            type="str",
            tooltip="Current generation status",
            allowed_modes={ParameterMode.OUTPUT, ParameterMode.PROPERTY},
            settable=False,
            default_value="",
            ui_options={"display_name": "Status"},
        )
        self.add_parameter(status_param)
        
        # Task ID output
        task_id_param = Parameter(
            name="task_id",
            output_type="str",
            type="str",
            tooltip="Unique task identifier for this generation",
            allowed_modes={ParameterMode.OUTPUT},
            settable=False,
            ui_options={"display_name": "Task ID"},
        )
        self.add_parameter(task_id_param)
        
        # Audio outputs (2 track variations)
        audio_track_1_param = Parameter(
            name="audio_track_1",
            output_type="AudioUrlArtifact",
            type="AudioUrlArtifact",
            tooltip="First generated music track",
            allowed_modes={ParameterMode.OUTPUT},
            settable=False,
            ui_options={"is_full_width": True, "display_name": "Audio Track 1", "pulse_on_run": True},
        )
        self.add_parameter(audio_track_1_param)
        
        audio_track_2_param = Parameter(
            name="audio_track_2",
            output_type="AudioUrlArtifact",
            type="AudioUrlArtifact",
            tooltip="Second generated music track (variation)",
            allowed_modes={ParameterMode.OUTPUT},
            settable=False,
            ui_options={"is_full_width": True, "display_name": "Audio Track 2", "pulse_on_run": True},
        )
        self.add_parameter(audio_track_2_param)
        
        # Cover image output
        cover_image_param = Parameter(
            name="cover_image",
            output_type="ImageUrlArtifact",
            type="ImageUrlArtifact",
            tooltip="Generated cover art image",
            allowed_modes={ParameterMode.OUTPUT},
            settable=False,
            ui_options={"display_name": "Cover Image"},
        )
        self.add_parameter(cover_image_param)
        
        # Generated title output
        generated_title_param = Parameter(
            name="generated_title",
            output_type="str",
            type="str",
            tooltip="Generated music title",
            allowed_modes={ParameterMode.OUTPUT},
            settable=False,
            ui_options={"display_name": "Generated Title"},
        )
        self.add_parameter(generated_title_param)
        
        # Tags output
        tags_param = Parameter(
            name="tags",
            output_type="str",
            type="str",
            tooltip="Generated music genre/style tags",
            allowed_modes={ParameterMode.OUTPUT},
            settable=False,
            ui_options={"display_name": "Tags"},
        )
        self.add_parameter(tags_param)
        
        # Lyrics output
        lyrics_param = Parameter(
            name="lyrics",
            output_type="str",
            type="str",
            tooltip="Generated or provided lyrics (shows '[Instrumental]' for instrumental tracks)",
            allowed_modes={ParameterMode.OUTPUT},
            settable=False,
            ui_options={"multiline": True, "display_name": "Lyrics"},
        )
        self.add_parameter(lyrics_param)
        
        # Result details output
        result_details_param = Parameter(
            name="result_details",
            output_type="str",
            type="str",
            tooltip="Detailed information about the generation result",
            allowed_modes={ParameterMode.OUTPUT},
            settable=False,
            ui_options={"multiline": True, "is_full_width": True, "display_name": "Result Details", "hide": True},
        )
        self.add_parameter(result_details_param)
        
        # Initialize parameter visibility
        self._initialize_parameter_visibility()

    def _initialize_parameter_visibility(self) -> None:
        """Initialize parameter visibility based on default mode."""
        custom_mode = self.get_parameter_value("custom_mode") or False
        if custom_mode:
            self.show_parameter_by_name("style")
            self.show_parameter_by_name("title")
        else:
            self.hide_parameter_by_name("style")
            self.hide_parameter_by_name("title")

    def after_value_set(self, parameter: Parameter, value: Any) -> None:
        """Update parameter visibility based on mode selection."""
        if parameter.name == "custom_mode":
            if value:
                self.show_parameter_by_name("style")
                self.show_parameter_by_name("title")
            else:
                self.hide_parameter_by_name("style")
                self.hide_parameter_by_name("title")
        
        return super().after_value_set(parameter, value)

    def _log(self, message: str) -> None:
        """Safe logging with exception suppression."""
        with suppress(Exception):
            logger.info(f"{self.name}: {message}")

    def _validate_api_key(self) -> str:
        """Validate and retrieve API key from secrets manager."""
        api_key = GriptapeNodes.SecretsManager().get_secret(self.API_KEY_NAME)
        if not api_key:
            raise ValueError(
                f"Missing {self.API_KEY_NAME}. Please configure your Suno API key in Settings > Secrets."
            )
        return api_key

    def validate_before_node_run(self) -> list[Exception] | None:
        """Validate parameters before running the node."""
        exceptions = []
        
        custom_mode = self.get_parameter_value("custom_mode")
        instrumental = self.get_parameter_value("instrumental")
        model = self.get_parameter_value("model")
        
        if custom_mode:
            # Custom mode validation
            style = self.get_parameter_value("style") or ""
            title = self.get_parameter_value("title") or ""
            prompt = self.get_parameter_value("prompt") or ""
            
            # Style is always required in custom mode
            if not style.strip():
                exceptions.append(ValueError(
                    f"{self.name}: Style is required in Custom Mode"
                ))
            
            # Title is always required in custom mode
            if not title.strip():
                exceptions.append(ValueError(
                    f"{self.name}: Title is required in Custom Mode"
                ))
            
            # Prompt is required if not instrumental
            if not instrumental and not prompt.strip():
                exceptions.append(ValueError(
                    f"{self.name}: Prompt/Lyrics required in Custom Mode when not instrumental"
                ))
            
            # Check prompt length limit
            if prompt:
                prompt_limit = self.PROMPT_LIMITS_CUSTOM.get(model, 3000)
                if len(prompt) > prompt_limit:
                    exceptions.append(ValueError(
                        f"{self.name}: Prompt exceeds {prompt_limit} character limit for {model} "
                        f"(current: {len(prompt)} characters)"
                    ))
            
            # Check style length limit
            if style:
                style_limit = self.STYLE_LIMITS.get(model, 200)
                if len(style) > style_limit:
                    exceptions.append(ValueError(
                        f"{self.name}: Style exceeds {style_limit} character limit for {model} "
                        f"(current: {len(style)} characters)"
                    ))
            
            # Check title length limit
            if title and len(title) > self.TITLE_LIMIT:
                exceptions.append(ValueError(
                    f"{self.name}: Title exceeds {self.TITLE_LIMIT} character limit "
                    f"(current: {len(title)} characters)"
                ))
        else:
            # Simple mode validation
            prompt = self.get_parameter_value("prompt") or ""
            
            if not prompt.strip():
                exceptions.append(ValueError(
                    f"{self.name}: Prompt is required in Simple Mode"
                ))
            
            if len(prompt) > self.PROMPT_LIMIT_SIMPLE:
                exceptions.append(ValueError(
                    f"{self.name}: Prompt exceeds {self.PROMPT_LIMIT_SIMPLE} character limit in Simple Mode "
                    f"(current: {len(prompt)} characters)"
                ))
        
        return exceptions if exceptions else None

    def _set_safe_defaults(self) -> None:
        """Set safe default values for all outputs."""
        self.parameter_output_values["status"] = "error"
        self.parameter_output_values["task_id"] = None
        self.parameter_output_values["audio_track_1"] = None
        self.parameter_output_values["audio_track_2"] = None
        self.parameter_output_values["cover_image"] = None
        self.parameter_output_values["generated_title"] = ""
        self.parameter_output_values["tags"] = ""
        self.parameter_output_values["lyrics"] = ""
        self.parameter_output_values["result_details"] = "Generation failed"

    def _build_payload(self) -> dict[str, Any]:
        """Build API request payload from parameters."""
        custom_mode = self.get_parameter_value("custom_mode")
        model = self.get_parameter_value("model")
        instrumental = self.get_parameter_value("instrumental")
        
        payload = {
            "customMode": custom_mode,
            "instrumental": instrumental,
            "model": model,
            "callBackUrl": "https://example.com/callback",  # Required by API, but we use polling instead
        }
        
        # Add prompt (always include if provided)
        prompt = self.get_parameter_value("prompt") or ""
        if prompt.strip():
            payload["prompt"] = prompt.strip()
        
        # Add custom mode specific fields
        if custom_mode:
            style = self.get_parameter_value("style") or ""
            title = self.get_parameter_value("title") or ""
            
            if style.strip():
                payload["style"] = style.strip()
            if title.strip():
                payload["title"] = title.strip()
        
        # Add optional parameters if not default
        negative_tags = self.get_parameter_value("negative_tags") or ""
        if negative_tags.strip():
            payload["negativeTags"] = negative_tags.strip()
        
        vocal_gender = self.get_parameter_value("vocal_gender")
        if vocal_gender and vocal_gender != "auto":
            payload["vocalGender"] = vocal_gender
        
        # Add weight parameters (only if not default 0.65)
        style_weight = self.get_parameter_value("style_weight")
        if style_weight and style_weight != 0.65:
            payload["styleWeight"] = round(style_weight, 2)
        
        weirdness = self.get_parameter_value("weirdness_constraint")
        if weirdness and weirdness != 0.65:
            payload["weirdnessConstraint"] = round(weirdness, 2)
        
        audio_weight = self.get_parameter_value("audio_weight")
        if audio_weight and audio_weight != 0.65:
            payload["audioWeight"] = round(audio_weight, 2)
        
        return payload

    def _submit_task(self, api_key: str) -> dict[str, Any]:
        """Submit music generation task to Suno API."""
        payload = self._build_payload()
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        # Log request (sanitized)
        with suppress(Exception):
            log_payload = payload.copy()
            if "prompt" in log_payload and len(log_payload["prompt"]) > 100:
                log_payload["prompt"] = log_payload["prompt"][:100] + "..."
            self._log(f"Submitting task: {json.dumps(log_payload, indent=2)}")
        
        try:
            response = requests.post(
                f"{self.API_BASE_URL}/generate",
                json=payload,
                headers=headers,
                timeout=self.DEFAULT_TIMEOUT,
            )
            response.raise_for_status()
            
            response_data = response.json()
            self._log(f"Task submission response: {json.dumps(response_data, indent=2)}")
            
            # Check response structure
            if response_data.get("code") != 200:
                error_msg = response_data.get("msg", "Unknown error")
                raise RuntimeError(f"API returned error: {error_msg}")
            
            return response_data
            
        except requests.exceptions.Timeout:
            raise RuntimeError(f"Request timed out after {self.DEFAULT_TIMEOUT} seconds")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Request failed: {str(e)}")

    def _poll_for_completion(self, task_id: str, api_key: str) -> dict[str, Any]:
        """Poll API for task completion using record-info endpoint.
        
        Status values:
        - PENDING: Task is waiting to be processed
        - TEXT_SUCCESS: Lyrics/text generation completed
        - FIRST_SUCCESS: First track generation completed
        - SUCCESS: All tracks generated successfully
        - CREATE_TASK_FAILED: Failed to create task
        - GENERATE_AUDIO_FAILED: Failed to generate music
        - CALLBACK_EXCEPTION: Error during callback
        - SENSITIVE_WORD_ERROR: Content contains prohibited words
        """
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        query_url = f"{self.API_BASE_URL}/generate/record-info"
        
        for attempt in range(self.MAX_POLLING_ATTEMPTS):
            time.sleep(self.POLLING_INTERVAL)
            
            try:
                response = requests.get(
                    query_url,
                    headers=headers,
                    params={"taskId": task_id},
                    timeout=self.DEFAULT_TIMEOUT,
                )
                response.raise_for_status()
                
                status_data = response.json()
                self._log(f"Polling attempt {attempt + 1}/{self.MAX_POLLING_ATTEMPTS}: {json.dumps(status_data, indent=2)}")
                
                # Check API response code
                if status_data.get("code") != 200:
                    error_msg = status_data.get("msg", "Unknown error")
                    raise RuntimeError(f"API returned error: {error_msg}")
                
                # Get task status from data object
                data = status_data.get("data", {})
                task_status = data.get("status", "")
                
                # Update status parameter with progress
                status_msg = f"Status: {task_status} ({attempt + 1}/{self.MAX_POLLING_ATTEMPTS})"
                self.set_parameter_value("status", status_msg)
                
                # Check if generation is complete
                if task_status == "SUCCESS":
                    self._log("Task completed successfully")
                    return status_data
                elif task_status in ["CREATE_TASK_FAILED", "GENERATE_AUDIO_FAILED", "CALLBACK_EXCEPTION", "SENSITIVE_WORD_ERROR"]:
                    error_msg = data.get("errorMessage", f"Task failed with status: {task_status}")
                    raise RuntimeError(f"Generation failed: {error_msg}")
                
                # Continue polling for PENDING, TEXT_SUCCESS, FIRST_SUCCESS
                
            except requests.exceptions.RequestException as e:
                self._log(f"Polling request failed: {e}")
                # Continue polling on temporary errors
        
        raise RuntimeError(
            f"Task did not complete within {self.MAX_POLLING_ATTEMPTS * self.POLLING_INTERVAL} seconds. "
            "The task may still be processing - check back with the task_id later."
        )

    def _extract_track_data(self, response_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract track data from completed task response.
        
        Response structure:
        {
          "data": {
            "response": {
              "sunoData": [
                {
                  "audioUrl": "...",
                  "imageUrl": "...",
                  "title": "...",
                  "duration": ...,
                  "tags": "...",
                  etc.
                }
              ]
            }
          }
        }
        """
        tracks = []
        
        data = response_data.get("data", {})
        if not isinstance(data, dict):
            return tracks
        
        response = data.get("response", {})
        if not isinstance(response, dict):
            return tracks
        
        suno_data = response.get("sunoData", [])
        if not isinstance(suno_data, list):
            return tracks
        
        for item in suno_data:
            track = {
                "audio_url": item.get("audioUrl"),
                "image_url": item.get("imageUrl"),
                "title": item.get("title"),
                "duration": item.get("duration"),
                "tags": item.get("tags"),
                "prompt": item.get("prompt"),
                "model_name": item.get("modelName"),
            }
            if track["audio_url"]:  # Only add if we have an audio URL
                tracks.append(track)
        
        return tracks
    
    @staticmethod
    def _download_bytes_from_url(url: str, timeout: int = 120) -> bytes | None:
        """Download bytes from URL."""
        try:
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp.content
        except Exception:
            return None
    
    def _save_audio_from_url(self, audio_url: str, track_index: int) -> AudioUrlArtifact | None:
        """Download audio from URL and save to static storage."""
        try:
            self._log(f"Downloading audio track {track_index}")
            
            # Download audio bytes
            audio_bytes = self._download_bytes_from_url(audio_url)
            if not audio_bytes:
                self._log(f"Failed to download audio track {track_index}")
                return AudioUrlArtifact(value=audio_url)  # Fallback to original URL
            
            # Generate filename with timestamp
            filename = f"suno_track{track_index}_{int(time.time())}.mp3"
            
            # Save to static storage
            static_files_manager = GriptapeNodes.StaticFilesManager()
            saved_url = static_files_manager.save_static_file(audio_bytes, filename)
            
            # Create AudioUrlArtifact
            self._log(f"Saved audio track {track_index} to static storage as {filename}")
            return AudioUrlArtifact(value=saved_url, name=filename)
            
        except Exception as e:
            self._log(f"Failed to save audio track {track_index}: {e}")
            return AudioUrlArtifact(value=audio_url)  # Fallback to original URL
    
    def _save_image_from_url(self, image_url: str) -> ImageUrlArtifact | None:
        """Download image from URL and save to static storage."""
        try:
            self._log("Downloading cover image")
            
            # Download image bytes
            image_bytes = self._download_bytes_from_url(image_url)
            if not image_bytes:
                self._log("Failed to download cover image")
                return ImageUrlArtifact(value=image_url)  # Fallback to original URL
            
            # Generate filename with timestamp
            filename = f"suno_cover_{int(time.time())}.jpeg"
            
            # Save to static storage
            static_files_manager = GriptapeNodes.StaticFilesManager()
            saved_url = static_files_manager.save_static_file(image_bytes, filename)
            
            # Create ImageUrlArtifact
            self._log(f"Saved cover image to static storage as {filename}")
            return ImageUrlArtifact(value=saved_url, name=filename)
            
        except Exception as e:
            self._log(f"Failed to save cover image: {e}")
            return ImageUrlArtifact(value=image_url)  # Fallback to original URL

    def process(self) -> AsyncResult[None]:
        """Process the music generation request asynchronously."""
        yield lambda: self._process()

    def _process(self) -> None:
        """Main processing method for music generation."""
        # Set safe defaults first
        self._set_safe_defaults()
        
        try:
            # Validate API key
            api_key = self._validate_api_key()
            
            # Update status
            self.set_parameter_value("status", "Submitting task...")
            
            # Submit task
            submission_response = self._submit_task(api_key)
            task_id = submission_response.get("data", {}).get("taskId")
            
            if not task_id:
                raise RuntimeError("No task ID returned from API")
            
            self.parameter_output_values["task_id"] = task_id
            self._log(f"Task submitted successfully: {task_id}")
            
            # Update status
            self.set_parameter_value("status", "Generating music...")
            
            # Poll for completion
            completion_response = self._poll_for_completion(task_id, api_key)
            
            # Extract track data
            tracks = self._extract_track_data(completion_response)
            
            if not tracks:
                raise RuntimeError("No tracks in completed response")
            
            self._log(f"Retrieved {len(tracks)} track(s) from API")
            
            # Process first track (always present)
            if len(tracks) >= 1:
                track1 = tracks[0]
                audio_artifact_1 = self._save_audio_from_url(track1["audio_url"], 1)
                self.parameter_output_values["audio_track_1"] = audio_artifact_1
                
                # Save cover image (from first track)
                if track1["image_url"]:
                    cover_artifact = self._save_image_from_url(track1["image_url"])
                    self.parameter_output_values["cover_image"] = cover_artifact
                
                # Set generated title (from first track)
                self.parameter_output_values["generated_title"] = track1["title"] or "Untitled"
                
                # Set tags (from first track)
                self.parameter_output_values["tags"] = track1["tags"] or ""
                
                # Set lyrics (from first track prompt field)
                self.parameter_output_values["lyrics"] = track1["prompt"] or ""
            
            # Process second track (if present)
            if len(tracks) >= 2:
                track2 = tracks[1]
                audio_artifact_2 = self._save_audio_from_url(track2["audio_url"], 2)
                self.parameter_output_values["audio_track_2"] = audio_artifact_2
            
            # Success - set status
            self.parameter_output_values["status"] = "complete"
            
            # Build detailed result message
            result_lines = [
                f"✓ Generated {len(tracks)} track variation(s)",
                f"Title: {tracks[0]['title']}",
                f"Tags: {tracks[0]['tags']}",
                f"Lyrics: {tracks[0]['prompt'][:50]}..." if len(tracks[0]['prompt']) > 50 else f"Lyrics: {tracks[0]['prompt']}",
                f"Task ID: {task_id}",
                f"Model: {tracks[0]['model_name']}",
                "",
                "Track Details:",
            ]
            for i, track in enumerate(tracks, 1):
                result_lines.append(f"{i}. Duration: {track['duration']}s")
                result_lines.append(f"   Audio: {track['audio_url']}")
                if i < len(tracks):
                    result_lines.append("")
            
            self.parameter_output_values["result_details"] = "\n".join(result_lines)
            
            self._log(f"Generation complete - {len(tracks)} tracks generated")
            
        except Exception as e:
            self._set_safe_defaults()
            error_msg = str(e)
            self.parameter_output_values["result_details"] = f"ERROR: {error_msg}"
            self._log(f"Generation failed: {error_msg}")
            raise RuntimeError(f"{self.name}: {error_msg}") from e

