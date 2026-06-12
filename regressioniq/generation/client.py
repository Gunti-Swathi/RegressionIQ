from __future__ import annotations

import os
from pathlib import Path
from collections.abc import Iterable
from typing import Protocol


class TestGenerationClient(Protocol):
    def generate(self, prompt: str) -> str:
        ...


class GeminiConfigurationError(RuntimeError):
    pass


def load_env_files(paths: Iterable[str | Path]) -> None:
    for path in paths:
        env_path = Path(path)
        if not env_path.exists() or not env_path.is_file():
            continue
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


class GeminiClient:
    def __init__(
        self,
        model: str = "gemini-2.5-flash",
        api_key: str | None = None,
        env_paths: Iterable[str | Path] | None = None,
    ) -> None:
        self.model = model
        if env_paths:
            load_env_files(env_paths)
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise GeminiConfigurationError(
                "Gemini API key not found. Set GEMINI_API_KEY or GOOGLE_API_KEY in your shell or .env file."
            )

    def generate(self, prompt: str) -> str:
        try:
            from google import genai  # type: ignore
        except ImportError:
            return self._generate_with_legacy_sdk(prompt)

        client = genai.Client(api_key=self.api_key)
        response = client.models.generate_content(model=self.model, contents=prompt)
        text = getattr(response, "text", None)
        if not text:
            raise GeminiConfigurationError("Gemini returned an empty response.")
        return text

    def _generate_with_legacy_sdk(self, prompt: str) -> str:
        try:
            import google.generativeai as genai  # type: ignore
        except ImportError as exc:
            raise GeminiConfigurationError(
                'Gemini SDK not installed. Install with: python3 -m pip install -e ".[llm]"'
            ) from exc

        genai.configure(api_key=self.api_key)
        response = genai.GenerativeModel(self.model).generate_content(prompt)
        text = getattr(response, "text", None)
        if not text:
            raise GeminiConfigurationError("Gemini returned an empty response.")
        return text
