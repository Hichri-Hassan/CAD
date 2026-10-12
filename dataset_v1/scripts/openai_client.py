"""OpenAI API client for automated prompt generation."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from config.env import load_project_env


DEFAULT_MODEL = "gpt-4o-mini"
API_URL = "https://api.openai.com/v1/chat/completions"

SYSTEM_PROMPT = """You are generating training data for a CAD Copilot.

Your task is to produce five different natural-language requests that a mechanical engineer or CAD user could realistically type when asking an AI to create a part.

The prompts should describe the visible geometry of the part, not the CAD operations used to build it.

Rules:
- Write in natural English.
- Imagine the user is requesting a CAD model from an AI assistant.
- Focus on the final geometry rather than the construction history.
- Use vocabulary such as: rectangular block, rectangular plate, base plate, bracket, cylindrical boss, through hole, blind hole, pocket, slot, rounded corner, chamfered edge, recessed area, rib, flange.
- Avoid CAD implementation terminology whenever possible.
- Do NOT use words such as: prismatic solid, extrusion, Pad, Pocket (as a FreeCAD feature), Sketch, feature tree, operation, PartDesign — unless absolutely necessary.
- Do NOT invent functionality. Never write things like: for weight reduction, serves as a foundation, for mounting, structural support, mechanical reinforcement — unless this can be directly inferred from the geometry.
- Describe only what is visible.

Diversity — generate five prompts with different styles, for example:
1. Very short request.
2. Natural conversational request.
3. Geometry-focused description.
4. Dimension-focused request (include important dimensions only if available).
5. Alternative wording using different vocabulary.

Avoid repeating the same sentence with different verbs like "Create", "Design", "Generate", and "Make". Each prompt should feel like it was written by a different person.

Dimensions:
- Only include dimensions when they add useful information.
- Do not mention every numerical value.
- If the model has many dimensions, mention only the most important ones.

Output — return JSON only:
{
  "title": "...",
  "description": "...",
  "tags": ["..."],
  "prompts": ["...", "...", "...", "...", "..."]
}

The title should be concise and describe the part.
The description should summarize the geometry in one or two sentences.
The prompts should sound realistic and natural, as if they were collected from real CAD users rather than generated automatically.

No markdown. No code fences. No explanations outside the JSON object."""


class OpenAIClientError(RuntimeError):
    """Raised when the OpenAI API call or response parsing fails."""


class OpenAIClient:
    """Minimal OpenAI chat-completions client using stdlib HTTP."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        timeout_seconds: int = 60,
    ) -> None:
        load_project_env()
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key or self.api_key.strip() in {"", "sk-xxxxxxxxxxxxxxxxxxxxxxxx"}:
            raise OpenAIClientError(
                "OPENAI_API_KEY is not set. Define it in the .env file at the project root:\n"
                "  OPENAI_API_KEY=sk-...\n"
                "Copy .env.example to .env if needed."
            )
        self.model = model
        self.timeout_seconds = timeout_seconds

    def generate_prompts(self, summary_text: str) -> dict[str, Any]:
        """Send a structured summary and receive validated prompt metadata."""
        payload = {
            "model": self.model,
            "temperature": 0.7,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Write training prompts for a part with the following geometry summary:\n\n"
                        f"{summary_text}"
                    ),
                },
            ],
        }
        response_data = self._post_json(payload)
        content = response_data["choices"][0]["message"]["content"]
        parsed = self._parse_json_content(content)
        self._validate_prompt_payload(parsed)
        return parsed

    def _post_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise OpenAIClientError(f"OpenAI API HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise OpenAIClientError(f"OpenAI API connection error: {exc}") from exc

        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise OpenAIClientError("OpenAI API returned non-JSON response.") from exc

    @staticmethod
    def _parse_json_content(content: str) -> dict[str, Any]:
        content = content.strip()
        if content.startswith("```"):
            content = content.strip("`")
            if content.lower().startswith("json"):
                content = content[4:].strip()
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise OpenAIClientError(f"Model returned invalid JSON: {content[:200]}") from exc
        if not isinstance(parsed, dict):
            raise OpenAIClientError("Model response must be a JSON object.")
        return parsed

    @staticmethod
    def _validate_prompt_payload(payload: dict[str, Any]) -> None:
        required = ("title", "description", "tags", "prompts")
        for field in required:
            if field not in payload:
                raise OpenAIClientError(f"Missing required field in model response: {field}")

        if not isinstance(payload["title"], str) or not payload["title"].strip():
            raise OpenAIClientError("Field 'title' must be a non-empty string.")
        if not isinstance(payload["description"], str) or not payload["description"].strip():
            raise OpenAIClientError("Field 'description' must be a non-empty string.")
        if not isinstance(payload["tags"], list) or not payload["tags"]:
            raise OpenAIClientError("Field 'tags' must be a non-empty list.")
        if not isinstance(payload["prompts"], list) or len(payload["prompts"]) != 5:
            raise OpenAIClientError("Field 'prompts' must contain exactly 5 strings.")
        if not all(isinstance(item, str) and item.strip() for item in payload["prompts"]):
            raise OpenAIClientError("Every prompt must be a non-empty string.")
