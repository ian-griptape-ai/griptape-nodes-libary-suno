# Changelog

All notable changes to the Suno Music Generation Node Library will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-10-24

### Added
- Initial release of Suno Music Generation node library
- `uv` dependency management with `pyproject.toml` and lock file
- `SunoGenerateMusic` node with full API integration
- Support for Custom Mode (full control) and Simple Mode (auto-generation)
- Support for all Suno model versions: V5, V4_5PLUS, V4_5, V4, V3_5
- Asynchronous task polling using `/generate/record-info` endpoint with `AsyncResult` pattern
- Real-time status updates showing task progress (PENDING → TEXT_SUCCESS → FIRST_SUCCESS → SUCCESS)
- Comprehensive parameter validation based on model and mode
- Dummy callback URL in API requests (required parameter, polling used for status)
- Advanced controls: vocal gender, negative tags, style weight, weirdness, audio weight
- AudioArtifact outputs for both generated tracks (automatically downloaded and saved)
- ImageArtifact output for generated cover art
- String output for generated title (as `generated_title` parameter)
- String output for generated genre/style tags
- String output for lyrics/prompt (shows "[Instrumental]" for instrumental tracks)
- Automatic file download and static storage integration
- Complete error handling and user-friendly error messages
- Detailed logging for debugging
- Rich result details with track metadata (duration, tags, model)
- Full documentation with examples and best practices

### Features
- **Two Generation Modes**: Custom Mode for full control, Simple Mode for quick generation
- **Multiple Models**: Choose from 5 different model versions
- **Vocal Control**: Select male/female vocals or create instrumental tracks
- **Style Customization**: Specify genres and exclude unwanted styles
- **Advanced Parameters**: Fine-tune generation with weight sliders
- **Status Tracking**: Real-time status updates during generation
- **Task Management**: Task ID output for tracking long-running generations

### Documentation
- Comprehensive README with installation instructions (both uv and pip)
- Usage guide and examples
- API reference and troubleshooting guide
- Model comparison table with character limits
- Example workflows for common use cases

