# Suno Music Generation Node Library

Generate AI-powered music tracks using the Suno API within Griptape Nodes. Create custom songs with your own lyrics, styles, and vocal preferences, or let AI auto-generate music from simple descriptions.

## Features

- **Two Generation Modes:**
  - **Custom Mode**: Full control over lyrics, style, and title
  - **Simple Mode**: Auto-generate music from prompt descriptions
  
- **Multiple Model Versions**: Choose from V5, V4_5PLUS, V4_5, V4, or V3_5
- **Vocal Control**: Select male/female vocals or create instrumental tracks
- **Style Customization**: Specify music genres and exclude unwanted styles
- **Advanced Parameters**: Fine-tune style weight, creativity, and audio influence
- **Dual Track Output**: Each generation produces 2 song variations with cover art
- **Audio Artifacts**: Outputs playable AudioArtifacts saved to static storage
- **Cover Art**: Automatically generated cover image for each song
- **Complete Metadata**: Outputs title, genre/style tags, and lyrics for each generation

## Installation

### Option 1: Using uv (Recommended)

1. Clone or download this library to your local machine
2. Install dependencies using [uv](https://docs.astral.sh/uv/):
   ```bash
   cd griptape-nodes-libary-suno
   uv sync
   ```
3. Place the library folder in your Griptape Nodes libraries directory
4. Configure your Suno API key in Settings > Secrets as `SUNO_API_KEY`

### Option 2: Automatic Installation

1. Place this folder in your Griptape Nodes libraries directory
2. The required dependencies (`requests`) will be installed automatically via pip
3. Configure your Suno API key in Settings > Secrets as `SUNO_API_KEY`

## Getting Started

### Simple Mode (Recommended for First-Time Users)

1. Add the "Suno Generate Music" node to your workflow
2. Leave "Custom Mode" unchecked
3. Enter a description in the "Prompt" field:
   ```
   A calm and relaxing piano track with soft melodies
   ```
4. Select your preferred model (V5 recommended)
5. Run the workflow

The node will auto-generate appropriate lyrics and create 2 music variations based on your description.

### Custom Mode (Full Control)

1. Check "Custom Mode" in the node
2. Fill in all required fields:
   - **Prompt/Lyrics**: The exact lyrics to sing (up to 3000-5000 chars depending on model)
   - **Style**: Music genre (e.g., "Classical", "Jazz", "Electronic")
   - **Title**: Song title (up to 80 characters)
3. Optionally check "Instrumental" to create music without vocals
4. Run the workflow

## Parameters

### Basic Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| Custom Mode | Boolean | Enable full control over lyrics/style vs auto-generation |
| Model | Dropdown | V5 (fastest), V4_5PLUS, V4_5, V4, or V3_5 |
| Prompt/Lyrics | Text | Description (Simple) or exact lyrics (Custom) |
| Style | Text | Music genre (Custom Mode only) |
| Title | Text | Song title (Custom Mode only) |
| Instrumental | Boolean | Generate without vocals |

### Advanced Parameters (Hidden by Default)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| Vocal Gender | Dropdown | auto | Preferred vocal gender (m/f/auto) |
| Negative Tags | Text | - | Styles to exclude (e.g., "Heavy Metal, Drums") |
| Style Weight | Slider | 0.65 | Strength of style guidance (0.0-1.0) |
| Weirdness | Slider | 0.65 | Creative deviation/novelty (0.0-1.0) |
| Audio Weight | Slider | 0.65 | Audio influence strength (0.0-1.0) |

### Output Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| Status | Text | Current generation status |
| Task ID | Text | Unique identifier for this generation |
| Audio Track 1 | AudioArtifact | First generated music track |
| Audio Track 2 | AudioArtifact | Second generated music track (variation) |
| Cover Image | ImageArtifact | Generated cover art |
| Generated Title | Text | Generated music title |
| Tags | Text | Generated genre/style tags |
| Lyrics | Text (multiline) | Generated or provided lyrics ("[Instrumental]" for instrumental tracks) |
| Result Details | Text | Detailed generation information with track metadata |

## Model Comparison

| Model | Max Duration | Quality | Speed | Character Limits |
|-------|--------------|---------|-------|------------------|
| V5 | 4 min | Superior expression | Fastest | Prompt: 5000, Style: 1000 |
| V4_5PLUS | 8 min | Richest sound | Fast | Prompt: 5000, Style: 1000 |
| V4_5 | 8 min | Superior blending | Fast | Prompt: 5000, Style: 1000 |
| V4 | 4 min | Best quality | Medium | Prompt: 3000, Style: 200 |
| V3_5 | 4 min | Creative diversity | Medium | Prompt: 3000, Style: 200 |

## Character Limits

### Custom Mode
- **Prompt (Lyrics)**: 3000 chars (V3_5/V4) or 5000 chars (V4_5+/V5)
- **Style**: 200 chars (V3_5/V4) or 1000 chars (V4_5+/V5)
- **Title**: 80 chars

### Simple Mode
- **Prompt (Description)**: 500 chars

## How It Works

The node uses an asynchronous polling approach with automatic artifact creation:

1. **Submit Task**: Sends generation request to Suno API
   - Includes a dummy callback URL (required by API)
   - Actual status checking done via polling
2. **Poll for Status**: Checks task status every 10 seconds
   - `PENDING`: Waiting to process
   - `TEXT_SUCCESS`: Lyrics generated
   - `FIRST_SUCCESS`: First track complete
   - `SUCCESS`: All tracks ready ✓
3. **Download & Save**: Downloads generated music and cover art
   - Saves audio files to static storage
   - Saves cover image to static storage
   - Creates AudioArtifact and ImageArtifact objects
4. **Output Results**: Provides 2 playable audio tracks, cover art, and title

The node provides real-time status updates during generation and automatically handles file storage.

## API Rate Limits

- **Concurrency**: 20 requests per 10 seconds
- **Generation Time**: 
  - Stream URLs available in 30-40 seconds
  - Downloadable URLs ready in 2-3 minutes (typical)
- **Polling**: Checks status every 10 seconds (max 6 minutes)
- **File Retention**: Generated files are kept for 15 days

## Example Workflows

### Example 1: Simple Relaxation Music

```
Custom Mode: ❌ (unchecked)
Model: V5
Prompt: "A peaceful meditation track with gentle nature sounds and ambient pads"
Instrumental: ✅ (checked)
```

### Example 2: Custom Rock Song

```
Custom Mode: ✅ (checked)
Model: V4_5PLUS
Prompt: "Verse 1:
Thunder rolls across the sky
Lightning strikes as we fly by
..."
Style: "Rock, Electric Guitar, Powerful Drums, Energetic"
Title: "Storm Riders"
Vocal Gender: m
```

### Example 3: Classical Piano Piece

```
Custom Mode: ✅ (checked)
Model: V5
Prompt: ""  (empty - instrumental)
Style: "Classical Piano, Romantic Era, Chopin Style"
Title: "Moonlight Reflection"
Instrumental: ✅ (checked)
```

## Error Handling

The node validates all parameters before generation:

- **Missing API Key**: Prompts to configure `SUNO_API_KEY` in Settings
- **Character Limits**: Validates prompt/style/title lengths for selected model
- **Required Fields**: Ensures all mode-specific requirements are met
- **Timeout Protection**: Max 6 minutes polling time (typical: 2-3 minutes)

## Troubleshooting

### "Missing SUNO_API_KEY"
Configure your API key in Settings > Secrets. Get your key from the [Suno API Dashboard](https://docs.sunoapi.org).

### "Task did not complete within timeout"
The task may still be processing. Use the `task_id` output to check status later, or try again with a simpler prompt.

### "Prompt exceeds character limit"
Check the character limits for your selected model and reduce prompt/style/title length accordingly.

### No music URLs in output
Verify your API key has sufficient credits. Check the API dashboard for account status.

## API Reference

This library uses the [Suno API v1](https://docs.sunoapi.org/suno-api/generate-music) for music generation.

### Endpoints Used
- `POST /api/v1/generate` - Submit generation task
- `GET /api/v1/query` - Poll for completion status

### Authentication
Bearer token authentication using your `SUNO_API_KEY`.

## Best Practices

1. **Start Simple**: Use Simple Mode first to understand the API
2. **Experiment with Models**: V5 is fastest, but V4_5PLUS offers richer sound
3. **Iterate on Styles**: Be specific with style descriptions for best results
4. **Use Negative Tags**: Exclude unwanted elements for more precise control
5. **Save Task IDs**: Keep task IDs for reference if you need to check status later
6. **Monitor Credits**: Each generation uses API credits (check dashboard)

## Support

For API-related issues:
- [Suno API Documentation](https://docs.sunoapi.org)
- [API Dashboard](https://api.sunoapi.org)

For node-related issues:
- Check Griptape Nodes logs for detailed error messages
- Verify all parameters meet validation requirements
- Ensure API key has sufficient credits

## License

This node library follows the Griptape Nodes licensing. The Suno API is a separate service with its own terms of service.

## Version History

### v1.0.0 (2025-10-24)
- Initial release
- Support for V5, V4_5PLUS, V4_5, V4, and V3_5 models
- Custom Mode and Simple Mode
- Asynchronous task polling with status updates
- Comprehensive parameter validation
- Advanced vocal and style controls

