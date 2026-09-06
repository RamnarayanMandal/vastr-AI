"""Gemini (Nano Banana) image generation/editing client.

Wraps the native ``generateContent`` REST endpoint for the Gemini image model
(e.g. ``gemini-3.1-flash-image``). Supports zero or more inline base64 reference
images plus a text prompt, and returns the generated image bytes.

All methods raise ``GeminiError`` (retryable-transient) or leave it to callers
to translate permanent problems into ``ProviderConfigurationError`` / pipeline
errors. Hidden behind the pipeline so callers never depend on the SDK.
"""

from __future__ import annotations

import base64
from typing import List, Optional

import httpx


class GeminiError(Exception):
    """Base error for Gemini client failures."""


class GeminiNotConfigured(GeminiError):
    """No GEMINI_API_KEY is set - image generation cannot run."""


class GeminiAPIError(GeminiError):
    """The Gemini API returned a non-success response (transient-ish)."""


def _mime_type(data: bytes) -> str:
    # Cheap sniff: JPEG magic bytes, PNG magic bytes, else default to JPEG.
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    return "image/jpeg"


def _build_payload(prompt: str, images: List[bytes], aspect_ratio: str = "3:4") -> dict:
    parts: List[dict] = []
    for img in images:
        parts.append(
            {
                "inline_data": {
                    "mime_type": _mime_type(img),
                    "data": base64.b64encode(img).decode("ascii"),
                }
            }
        )
    parts.append({"text": prompt})
    return {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
            "imageConfig": {
                "aspectRatio": aspect_ratio,
                "imageSize": "1K",
            },
        },
    }


def _extract_image_bytes(response_json: dict) -> Optional[bytes]:
    try:
        candidates = response_json["candidates"]
        for part in candidates[0]["content"]["parts"]:
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                return base64.b64decode(inline["data"])
    except (KeyError, IndexError, TypeError, ValueError):
        return None
    return None


def generate_image(
    prompt: str,
    images: Optional[List[bytes]] = None,
    aspect_ratio: str = "3:4",
    api_key: str = "",
    model: str = "",
    base_url: str = "",
    timeout: Optional[float] = None,
) -> bytes:
    """Run Gemini image generation/editing and return the image bytes.

    ``images`` are passed inline as reference images (person photo, fabric
    swatch, rendered garment) alongside ``prompt``. Raises ``GeminiError``.
    """
    from ..config import settings as _s

    key = api_key or _s.gemini_api_key
    if not key:
        raise GeminiNotConfigured(
            "Gemini image generation requires GEMINI_API_KEY to be set."
        )
    model_id = model or _s.gemini_model
    base = (base_url or _s.gemini_base_url).rstrip("/")
    url = f"{base}/models/{model_id}:generateContent"

    payload = _build_payload(prompt, images or [], aspect_ratio)
    headers = {"x-goog-api-key": key, "Content-Type": "application/json"}

    try:
        resp = httpx.post(
            url,
            headers=headers,
            json=payload,
            timeout=timeout or _s.gemini_timeout,
        )
    except httpx.HTTPError as exc:
        raise GeminiAPIError(f"Gemini request failed: {exc}")

    if resp.status_code != 200:
        body = resp.text[:500]
        raise GeminiAPIError(
            f"Gemini API error {resp.status_code}: {body}"
        )

    try:
        data = resp.json()
    except ValueError:
        raise GeminiAPIError("Gemini returned an unparseable response.")

    img = _extract_image_bytes(data)
    if not img:
        raise GeminiAPIError(
            "Gemini returned no image (check prompt / model / billing for image generation)."
        )
    return img


def garment_prompts(garment_type: str, garment_style: str, analysis: Optional[dict]) -> dict:
    """Human-readable fabric descriptive text used to seed generation prompts.

    The text is supplementary only - the uploaded garment reference image is
    the authoritative source for garment appearance and is passed to the model
    through the provider's image-reference channel.

    The selected garment type + style are hardened through
    ``services.garment_spec`` (silhouette/construction constraints and the
    rule that the style refines the garment and never replaces it).
    """
    from . import garment_spec

    pal = []
    if analysis:
        pal.append(f"dominant color {analysis.get('dominant_hex', '')}")
        extra = [c for c in (analysis.get("palette") or []) if c and c != analysis.get("dominant_hex", "")]
        if extra:
            pal.append(f"secondary colors {' '.join(extra[:2])}")
        if analysis.get("has_pattern") is not None:
            pal.append(
                "patterned" if analysis.get("has_pattern") else "solid"
            )
        if analysis.get("brightness") is not None:
            pal.append(
                "bright" if analysis["brightness"] > 0.6 else "dark"
            )
    fabric_desc = ", ".join(t for t in pal if t) or "a plain fabric"
    marker = "authoritative source for the garment appearance"
    spec = (
        f"{garment_spec.priority_rule(garment_type)} The product must be "
        f"{garment_spec.garment_type_constraint(garment_type)} "
        f"{garment_spec.garment_negative_constraint(garment_type, garment_style)} "
        f"{garment_spec.style_constraint(garment_type, garment_style)} "
    )
    spec_tryon = (
        f"{garment_spec.priority_rule(garment_type)} The garment worn must be "
        f"{garment_spec.garment_type_constraint(garment_type)} "
        f"{garment_spec.garment_negative_constraint(garment_type, garment_style)} "
        f"{garment_spec.style_constraint(garment_type, garment_style)} "
    )
    name = (
        f"{garment_spec.display_name(garment_style)} "
        f"{garment_spec.display_name(garment_type)}"
    )
    return {
        "garment": (
            "Create a flat, front-facing, full garment product image of a "
            f"{name}. {spec} [image 1] is the fabric/garment "
            f"reference image and is the {marker} for the garment appearance. "
            f"Use the described fabric details only as supplementary hints "
            f"({fabric_desc}). Reproduce Image 1's exact original colors, color "
            f"combinations, checks or checkered patterns, stripes, prints, "
            f"textures, motifs, borders, logos and visible construction "
            f"details. Do not recolor, reinterpret, redesign, simplify, or "
            f"replace the pattern - in particular do not turn a patterned "
            f"reference into a solid color. Preserve pattern scale and "
            f"orientation, and change only placement onto the flat garment "
            f"silhouette. Plain pale-gray background, studio lighting, no "
            f"person, no mannequin, no text."
        ),
        "tryon": (
            f"Dress the person in this photo in a {name}. "
            f"{spec_tryon} [image 1] is the person photo - keep their face, hair, pose, skin "
            f"tone and body exactly as they are, and only replace their "
            f"clothing. [image 2] is the garment reference image and is the "
            f"{marker} - use only its garment for the clothes, and use the "
            f"described fabric details only as supplementary hints "
            f"({fabric_desc}). Preserve Image 2's exact original colors, color "
            f"combinations, patterns, prints, checks, stripes, textures, "
            f"motifs, borders, and visible construction details. Do not "
            f"reinterpret, redesign, recolor, simplify, or replace the garment "
            f"design. If Image 2 contains a checkered or striped pattern, "
            f"reproduce that pattern clearly and consistently instead of "
            f"converting it into a solid color. The generated garment must "
            f"visually match the Image 2 garment reference as closely as "
            f"possible while naturally fitting the person's body. Change only "
            f"the garment placement, scale, deformation, and lighting required "
            f"to realistically fit the person - do not change the garment's "
            f"original design or colors. Photorealistic, consistent lighting, "
            f"no extra people, no text."
        ),
    }
