import json
import logging
import re
from abc import ABC, abstractmethod

from openai import OpenAI

from backend.services.indexing.contracts import SemanticArtifacts
from backend.services.indexing.provider_models import SemanticEnrichmentRequest

logger = logging.getLogger(__name__)

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", re.DOTALL)


def _extract_json(raw: str) -> dict:
    """Parse JSON from a model response, stripping markdown code fences if present."""
    if not raw or not raw.strip():
        raise ValueError("empty response from enrichment model")

    stripped = raw.strip()

    # Try to extract from markdown code fence
    m = _JSON_FENCE_RE.match(stripped)
    if m:
        stripped = m.group(1).strip()

    return json.loads(stripped)

_ENRICHMENT_PROMPT = (
    "Analyze this photo and return a JSON object with the following fields:\n"
    '- "ai_caption": a detailed English caption describing the photo (1-2 sentences)\n'
    '- "ai_short_caption": a short caption under 10 words\n'
    '- "scene_tags": list of scene-related tags\n'
    '- "mood_tags": list of mood/atmosphere tags\n'
    '- "style_tags": list of style tags\n'
    '- "composition_tags": list of composition tags\n'
    '- "lighting_tags": list of lighting tags\n'
    '- "color_tags": list of color-related tags\n'
    '- "subject_tags": list of subject tags\n'
    '- "use_case_tags": list of use case tags\n'
    '- "dominant_colors": list of hex color codes for the dominant colors\n'
    '- "has_human": boolean\n'
    '- "has_face": boolean\n'
    '- "is_abstract": boolean\n'
    '- "is_minimal": boolean\n'
    '- "is_dark": boolean\n\n'
    "Photo context — description: {analysis_text}\n"
    "Search text: {search_text}\n\n"
    "Return ONLY valid JSON, no other text."
)


class SemanticEnricher(ABC):
    @abstractmethod
    def enrich(self, *, image_url: str, analysis_text: str, search_text: str) -> SemanticArtifacts: ...


class StubSemanticEnricher(SemanticEnricher):
    def enrich(self, *, image_url: str, analysis_text: str, search_text: str) -> SemanticArtifacts:
        request = SemanticEnrichmentRequest(
            image_url=image_url,
            analysis_text=analysis_text,
            search_text=search_text,
        )
        return SemanticArtifacts(
            ai_caption=f"A {request.search_text} scene.",
            ai_short_caption=request.search_text,
            scene_tags=["wallpaper", "scenic"],
            mood_tags=["calm"],
            style_tags=["minimal"],
            has_human=True if "person" in request.search_text.lower() or "human" in request.search_text.lower() else False,
            has_face=False,
        )


class OpenAISemanticEnricher(SemanticEnricher):
    def __init__(self, *, client: OpenAI, model: str) -> None:
        self._client = client
        self._model = model

    def enrich(self, *, image_url: str, analysis_text: str, search_text: str) -> SemanticArtifacts:
        request = SemanticEnrichmentRequest(
            image_url=image_url,
            analysis_text=analysis_text,
            search_text=search_text,
        )
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": _ENRICHMENT_PROMPT.format(
                            analysis_text=request.analysis_text,
                            search_text=request.search_text,
                        )},
                        {"type": "image_url", "image_url": {"url": request.image_url}},
                    ],
                }
            ],
            temperature=0.3,
            max_tokens=1000,
        )
        raw = response.choices[0].message.content or ""
        try:
            data = _extract_json(raw)
        except Exception:
            logger.error("[enrichment] failed to parse response: %s", raw[:500])
            raise
        return SemanticArtifacts(
            ai_caption=data.get("ai_caption"),
            ai_short_caption=data.get("ai_short_caption"),
            scene_tags=data.get("scene_tags", []),
            mood_tags=data.get("mood_tags", []),
            style_tags=data.get("style_tags", []),
            composition_tags=data.get("composition_tags", []),
            lighting_tags=data.get("lighting_tags", []),
            color_tags=data.get("color_tags", []),
            subject_tags=data.get("subject_tags", []),
            use_case_tags=data.get("use_case_tags", []),
            dominant_colors=data.get("dominant_colors", []),
            has_human=data.get("has_human"),
            has_face=data.get("has_face"),
            is_abstract=data.get("is_abstract"),
            is_minimal=data.get("is_minimal"),
            is_dark=data.get("is_dark"),
        )


def build_semantic_enricher(settings) -> SemanticEnricher:
    if settings.mock_enrichment:
        return StubSemanticEnricher()
    client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
    return OpenAISemanticEnricher(client=client, model=settings.enrichment_model)
