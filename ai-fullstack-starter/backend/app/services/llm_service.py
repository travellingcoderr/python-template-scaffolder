from app.core.config import settings


class LLMService:
    def get_runtime_config(self) -> dict[str, str | bool]:
        provider = settings.LLM_PROVIDER.strip().lower() or "openai"
        return {
            "provider": provider,
            "model": settings.resolved_llm_model(),
            "has_openai_key": bool(settings.OPENAI_API_KEY),
            "has_gemini_key": bool(settings.GEMINI_API_KEY),
        }
