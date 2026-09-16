import os

ALLOWED_ZERO_COST_PROVIDERS = {
    'google_trends', 'youtube_free', 'gemini_free', 'pexels_free',
    'kokoro_local', 'ffmpeg_local'
}


def assert_zero_cost_provider(provider: str) -> None:
    if provider not in ALLOWED_ZERO_COST_PROVIDERS:
        raise RuntimeError(f"Provider '{provider}' is not approved for zero-cost mode")


def require_env(name: str) -> str:
    value = os.getenv(name, '').strip()
    if not value:
        raise RuntimeError(f'Missing required environment variable: {name}')
    return value
