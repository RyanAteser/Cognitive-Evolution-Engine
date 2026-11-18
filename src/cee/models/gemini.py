"""Optional Gemini provider; uses only controls exposed by the public API."""
import os

from cee.core.schemas import Candidate, Task
from cee.models.base import ModelResponse


class GeminiProvider:
    def __init__(self, model: str | None = None):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise RuntimeError('Install with: pip install -e ".[gemini]"') from exc
        self.client = genai.Client(api_key=api_key)
        self.types = types
        self.model = model or os.getenv("CEE_MODEL", "gemini-2.5-flash")

    def generate(self, candidate: Candidate, task: Task) -> ModelResponse:
        config = self.types.GenerateContentConfig(
            system_instruction=candidate.system_prompt,
            temperature=candidate.temperature,
            top_p=candidate.top_p,
            max_output_tokens=candidate.max_output_tokens,
        )
        response = self.client.models.generate_content(
            model=self.model, contents=task.prompt, config=config
        )
        usage = getattr(response, "usage_metadata", None)
        return ModelResponse(
            response.text or "",
            self.model,
            getattr(usage, "prompt_token_count", None),
            getattr(usage, "candidates_token_count", None),
        )
