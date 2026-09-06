"""Prompt construction for the VastrAI image generation workflow.

Uses LangChain ``PromptTemplate`` to build structured, reusable prompts for the
two model calls that make up the raw-fabric -> garment -> person workflow:

  1. fabric swatch -> flat garment rendering
  2. person + garment -> virtual try-on

The templates are seeded with a human-readable fabric description produced by
``services.gemini.garment_prompts`` (colour / pattern / brightness), so the
selected RAW FABRIC genuinely influences the generated garment - the model is
never asked to invent a fabric or reuse a stock garment image.
"""

from __future__ import annotations

from typing import Optional

from langchain_core.prompts import PromptTemplate

from . import garment_spec
from .gemini import garment_prompts as _fabric_descriptions


class VastrAIPrompts:
    """LangChain-backed prompt templates for garment + try-on generation.

    Providers use ``build_garment`` / ``build_tryon`` to render the final
    instruction strings, or call the LangChain ``PromptTemplate`` directly to
    compose a chain. Keeping the templates here (rather than inline) makes the
    model invocation a single, testable, provider-agnostic unit.

    The selected GARMENT TYPE is injected as a HARD CONSTRAINT (silhouette +
    construction + negative list, see ``services.garment_spec``); the STYLE is
    injected as a modifier that acts on that garment and never replaces it.
    """

    # Marker the workflow uses to prove fidelity instructions reached the prompt.
    PRESERVATION_MARKER = "authoritative source for the garment appearance"

    def __init__(self) -> None:
        self.garment_template = PromptTemplate.from_template(
            "Create a flat, front-facing, full garment product image of a "
            "{garment_style} {garment_type}. {garment_priority} The product "
            "must be {garment_type_constraint} {garment_negative_constraint} "
            "{style_constraint} [image 1] is the fabric/garment "
            "reference image and is the {preservation_marker} for the garment "
            "appearance. Use the described fabric details only as supplementary "
            "hints ({fabric_description}). Reproduce Image 1's exact original "
            "colors, color combinations, checks or checkered patterns, "
            "stripes, prints, textures, motifs, borders, logos and visible "
            "construction details. Do not recolor, reinterpret, redesign, "
            "simplify, or replace the pattern - in particular do not turn a "
            "patterned reference into a solid color. Preserve pattern scale and "
            "orientation, and change only placement onto the flat garment "
            "silhouette. Plain pale-gray background, studio lighting, no "
            "person, no mannequin, no text."
        )
        self.tryon_template = PromptTemplate.from_template(
            "Dress the person in this photo in a {garment_style} {garment_type}. "
            "{garment_priority} The garment worn must be "
            "{garment_type_constraint} {garment_negative_constraint} "
            "{style_constraint} [image 1] is the person photo - keep "
            "their face, hair, pose, skin tone and body exactly as they are, "
            "and only replace their clothing. [image 2] is the garment "
            "reference image and is the {preservation_marker} - use only its "
            "garment for the clothes, and use the described fabric details "
            "only as supplementary hints ({fabric_description}). Preserve "
            "Image 2's exact original colors, color combinations, patterns, "
            "prints, checks, stripes, textures, motifs, borders, and visible "
            "construction details. Do not reinterpret, redesign, recolor, "
            "simplify, or replace the garment design. If Image 2 contains a "
            "checkered or striped pattern, reproduce that pattern clearly and "
            "consistently instead of converting it into a solid color. The "
            "generated garment must visually match the Image 2 garment "
            "reference as closely as possible while naturally fitting the "
            "person's body. Change only the garment placement, scale, "
            "deformation, and lighting required to realistically fit the "
            "person - do not change the garment's original design or colors. "
            "Photorealistic, consistent lighting, no extra people, no text."
        )

    def fabric_description(self, analysis: Optional[dict]) -> str:
        """Human-readable, supplementary metadata from the fabric analysis.

        This text is never a substitute for the reference image - it is only a
        hint. Primary source of truth for garment appearance is the uploaded
        reference image passed through the provider's image-reference channel.
        """
        pal = []
        if analysis:
            if analysis.get("dominant_hex"):
                pal.append(f"dominant colour {analysis.get('dominant_hex')}")
            extra = [c for c in (analysis.get("palette") or []) if c and c != analysis.get("dominant_hex")]
            if extra:
                pal.append(f"secondary colours {' '.join(extra[:2])}")
            if analysis.get("has_pattern") is not None:
                pal.append("patterned" if analysis.get("has_pattern") else "solid")
            if analysis.get("brightness") is not None:
                pal.append("bright" if analysis["brightness"] > 0.6 else "dark")
        return ", ".join(t for t in pal if t) or "a plain fabric"

    def _template_kwargs(self, garment_type: str, garment_style: str, analysis: Optional[dict]) -> dict:
        return {
            "garment_type": garment_spec.display_name(garment_type),
            "garment_style": garment_spec.display_name(garment_style),
            "garment_priority": garment_spec.priority_rule(garment_type),
            "garment_type_constraint": garment_spec.garment_type_constraint(
                garment_type
            ),
            "garment_negative_constraint": garment_spec.garment_negative_constraint(
                garment_type, garment_style
            ),
            "style_constraint": garment_spec.style_constraint(
                garment_type, garment_style
            ),
            "fabric_description": self.fabric_description(analysis),
        }

    def build_garment(
        self, garment_type: str, garment_style: str, analysis: Optional[dict]
    ) -> str:
        return self.garment_template.format(
            preservation_marker=self.PRESERVATION_MARKER,
            **self._template_kwargs(garment_type, garment_style, analysis),
        )

    def build_tryon(
        self, garment_type: str, garment_style: str, analysis: Optional[dict]
    ) -> str:
        return self.tryon_template.format(
            preservation_marker=self.PRESERVATION_MARKER,
            **self._template_kwargs(garment_type, garment_style, analysis),
        )

    def build(
        self, garment_type: str, garment_style: str, analysis: Optional[dict]) -> dict:
        """Structured prompt payload: ``{"garment": ..., "tryon": ...}``."""
        return {
            "garment": self.build_garment(garment_type, garment_style, analysis),
            "tryon": self.build_tryon(garment_type, garment_style, analysis),
        }

    @staticmethod
    def constraint_flags(garment_type: str, garment_style: str) -> dict:
        """Audit flags for whether type/style constraints reached the prompt."""
        return garment_spec.constraint_flags(garment_type, garment_style)

    @staticmethod
    def audit_request(
        task: str,
        garment_type: str,
        garment_style: str,
        reference_attached: bool = True,
    ) -> None:
        """Temporary debug log emitted immediately before an AI request.

        No API keys, image data or other sensitive content is logged - only the
        garment type, style, whether the reference image is attached, and
        whether the type/style constraints reached the prompt.
        """
        flags = VastrAIPrompts.constraint_flags(garment_type, garment_style)
        print(
            f"[TRYON][GARMENT] task={task} type={garment_type} "
            f"style={garment_style} reference_attached="
            f"{str(bool(reference_attached)).lower()}",
            flush=True,
        )
        print(
            f"[TRYON][PROMPT] garment_type_constraint="
            f"{str(flags['garment_type_constraint']).lower()} "
            f"style_constraint={str(flags['style_constraint']).lower()}",
            flush=True,
        )


def build_garment_prompt(
    garment_type: str, garment_style: str, analysis: Optional[dict]
) -> str:
    """Module-level convenience mirror of the existing ``image_gen`` helper."""
    from .gemini import garment_prompts as _legacy

    return _legacy(garment_type, garment_style, analysis)["garment"]


def build_tryon_prompt(
    garment_type: str, garment_style: str, analysis: Optional[dict]
) -> str:
    from .gemini import garment_prompts as _legacy

    return _legacy(garment_type, garment_style, analysis)["tryon"]


def fabric_descriptions(analysis: Optional[dict]) -> dict:
    """Return the fabric description dict used to seed prompts."""
    return _fabric_descriptions("", "", analysis)
