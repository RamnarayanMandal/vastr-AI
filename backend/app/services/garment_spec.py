"""Garment type + style prompt knowledge base.

The selected GARMENT TYPE is a HARD CONSTRAINT: it must control the complete
silhouette and construction of the generated garment. The STYLE is a modifier
that acts *on* that garment (neckline / fit / sleeves / detailing) and must
never replace, re-categorise or genericise the garment type. The priority
order is:

    1. Garment type
    2. Garment reference image  (colors / pattern / texture / material)
    3. Garment style
    4. Fabric / color / pattern description
    5. Natural body fitting

Keys mirror the type/style IDs in ``mobile/src/constants/garments.ts`` but are
normalized (lowercase, spaces/hyphens -> underscores) so both raw IDs
(``boat_neck``) and natural text (``"boat neck"``) resolve to the same entry.
Everything here is plain-language text that is injected verbatim into the
generation prompt - nothing is hard-coded for a single type.
"""

from __future__ import annotations


def normalize(value: str) -> str:
    """Normalize a type/style id or human phrase to a canonical lookup key."""
    return (
        (value or "").strip().lower().replace(" ", "_").replace("-", "_")
    )


def display_name(value: str) -> str:
    """Human-readable display form (underscores -> spaces, original casing)."""
    return (value or "").strip().replace("_", " ")


# ---------------------------------------------------------------------------
# Garment type knowledge base
#
#   key -> (silhouette_and_construction_sentence, forbidden_categories)
# ---------------------------------------------------------------------------

GARMENT_SPECS: dict[str, tuple[str, tuple[str, ...]]] = {
    "blouse": (
        "a women's blouse with unmistakable feminine blouse silhouette and "
        "construction - a fitted, structured top with bust and waist shaping "
        "(darts and seaming), a blouse-length hem around the hip line, and "
        "sleeves consistent with the selected style. It must read INSTANTLY "
        "as a blouse: it must NOT become a shirt, a kurta or a tunic. No "
        "menswear markers - no full shirt button placket, no shirt collar "
        "points, no mandarin or stand collar, no kurta side slits or "
        "hip-to-knee straight ethnic cut.",
        (
            "general t-shirt",
            "generic top",
            "tunic",
            "oversized top",
            "casual shirt",
            "kurta",
            "kurti",
            "ethnic straight-cut top",
            "slit-side ethnic top",
            "men's shirt",
            "men's button-down shirt",
            "women's collared button-down shirt",
            "shirt collar",
            "shirt button placket",
            "mandarin collar",
            "stand collar",
            "polo collar",
            "hoodie",
            "generic sleeveless top",
            "loose or unstructured torso",
        ),
    ),
    "shirt": (
        "a shirt with shirt-specific construction and silhouette - a collared "
        "button-down shirt with a button placket down the front, a structured "
        "collar, cuffs on the sleeves, and fitted shoulders and torso. It must "
        "clearly be a shirt with shirt tailoring, never a blouse, top or knit.",
        (
            "blouse",
            "women's blouse",
            "top",
            "t-shirt",
            "tunic",
            "kurti",
            "hoodie",
            "unstructured oversized cut",
        ),
    ),
    "t_shirt": (
        "a classic T-shirt with unmistakable T-shirt construction - short "
        "sleeves, a simple crew-neck round collar, a relaxed straight-fit "
        "body and no formal tailoring. It must clearly be a T-shirt.",
        (
            "blouse",
            "collared button-down shirt",
            "tunic",
            "kurti",
            "dressy women's top",
            "tailored formal wear",
        ),
    ),
    "kurti": (
        "a kurti with traditional kurti construction and silhouette - from "
        "hip- to knee-length with a straight or gentle A-line cut, side slits, "
        "a kurti collar/neckline with a front placket, and three-quarter to "
        "full-length sleeves. It must clearly read as a kurti, not a western "
        "top or tunic.",
        (
            "western blouse",
            "t-shirt",
            "slim-fit western top",
            "wrap top",
            "tank top",
        ),
    ),
    "kurta": (
        "a men's kurta with traditional kurta construction - a knee- to "
        "calf-length straight-cut top with side slits, a band or mandarin "
        "collar, and full sleeves. It must clearly read as a kurta.",
        (
            "western shirt",
            "t-shirt",
            "kurti-style women's cut",
            "jacket",
            "suit coat",
        ),
    ),
    "saree_blouse": (
        "a traditional saree blouse (choli) with its classic fitted "
        "construction - midriff- to waist-length, a snug fitted bust with "
        "darts, minimal short sleeves, and a back opening with hooks or "
        "strings. It must clearly read as a saree blouse worn under a saree, "
        "not as a generic women's top.",
        (
            "generic women's top",
            "t-shirt",
            "western blouse",
            "tunic",
            "full-length top",
            "crop hoodie",
        ),
    ),
    "choli": (  # alias for saree_blouse
        "a traditional choli/saree blouse with its classic fitted "
        "construction - midriff- to waist-length, snug fitted bust, minimal "
        "short sleeves and a back opening. It must clearly read as a saree "
        "blouse, not as a generic women's top.",
        ("generic women's top", "t-shirt", "western blouse", "tunic"),
    ),
    "saree": (
        "a saree (sari) with an elegant traditional drape in which the visible "
        "garment on the upper body is a fitted saree blouse (choli) draped "
        "with the saree around the body. The blouse must read as a saree "
        "blouse, never a generic top.",
        (
            "generic women's top",
            "western blouse",
            "t-shirt",
            "dress",
            "lehenga",
        ),
    ),
    "top": (
        "a women's top with a fashionable, structured top silhouette - a "
        "fitted bodice with clean seams, appropriately tailored for the "
        "selected style, and clearly a designed top rather than a plain "
        "T-shirt or shirt.",
        (
            "t-shirt",
            "blouse with blouse-specific tailoring",
            "men's shirt",
            "tunic",
            "sweatshirt",
            "hoodie",
        ),
    ),
    "dress": (
        "a dress with a clear one-piece dress silhouette - a defined fitted "
        "bodice flowing into a skirt, constructed as a single dress garment.",
        ("two-piece top and skirt", "tunic", "separate shirt", "blouse"),
    ),
    "salwar_suit": (
        "a salwar suit - a traditional kameez (long tunic with a straight or "
        "A-line cut, side slits and a collar/neckline) paired with salwar "
        "pants and a dupatta drape. The kameez must read as traditional wear.",
        ("western blouse", "t-shirt", "bodycon dress", "lehenga"),
    ),
    "palazzo": (
        "palazzo pants with a high waist and wide, flowing wide-leg trousers "
        "that flare from the hip, clearly palazzo trousers.",
        ("tight tapered trousers", "jeans", "straight leg pants"),
    ),
    "lehenga": (
        "a lehenga - a flared traditional skirt with a fitted waistband and a "
        "full flared skirt worn as festive/traditional wear.",
        ("western skirt", "pants", "dress", "saree"),
    ),
    "dupatta": (
        "a dupatta - a long rectangular traditional stole/scarf draped over "
        "the shoulders or arms as part of the outfit.",
        ("saree", "western scarf", "jacket"),
    ),
    "pant": (
        "trousers/pants with clean tailored construction - a defined "
        "waistband, a structured leg, and proper pant fit and length.",
        ("jeans", "shorts", "leggings"),
    ),
    "jeans": (
        "denim jeans with classic jean construction - sturdy denim, a defined "
        "waistband, a button/zip fly, five-pocket styling, and straight or "
        "tapered legs.",
        ("trousers", "shorts", "jeggings"),
    ),
    "frock": (
        "a frock cut for a child - a sweet knee- to mid-calf-length dress "
        "with a fitted bodice and a flared or tiered skirt.",
        ("top and skirt separates", "tunic"),
    ),
    "ethnic_wear": (
        "traditional ethnic wear for a child - a kurta set or ethnic dress "
        "with a traditional silhouette and detailing.",
        ("western t-shirt", "casual jeans outfit"),
    ),
    "jacket": (
        "a jacket with a structured outerwear silhouette - a fitted or "
        "relaxed-cut jacket with sleeves, a front closure, and proper "
        "outerwear construction.",
        ("sweatshirt", "cardigan knit", "blazer only"),
    ),
    "suit": (
        "a tailored suit ensemble - a structured blazer jacket with matching "
        "trousers, sharp formal lines and proper suit tailoring.",
        ("casual jacket", "sweatshirt", "blazer without trousers"),
    ),
}


# ---------------------------------------------------------------------------
# Style knowledge base
#
#   key -> (apply_sentence, forbidden_style_list)
# ---------------------------------------------------------------------------

STYLE_SPECS: dict[str, tuple[str, tuple[str, ...]]] = {
    "boat_neck": (
        "apply a BOAT neckline - a wide neckline that runs horizontally "
        "across the collarbone and extends toward the shoulders (bateau "
        "style), and keep it as the garment's neckline throughout.",
        (
            "round neck",
            "V-neck",
            "sweetheart neckline",
            "polo or stand collar",
            "collared neckline",
        ),
    ),
    "round_neck": (
        "apply a ROUND crew neckline - a simple curved collar around the "
        "neck, and keep it as the garment's neckline throughout.",
        (
            "V-neck",
            "boat neck",
            "sweetheart neckline",
            "polo collar",
            "collared neckline",
        ),
    ),
    "v_neck": (
        "apply a V-neckline - a neckline that dips in a 'V' shape at the "
        "center front, and keep it as the garment's neckline throughout.",
        (
            "round neck",
            "boat neck",
            "sweetheart neckline",
            "polo collar",
        ),
    ),
    "designer": (
        "apply designer-level detailing to the garment without changing its "
        "category - refined trims, embellishments, premium fabric handling, a "
        "modern cut and a polished high-end finish, all applied to the "
        "selected garment type (e.g. a designer blouse stays a blouse)."
    ),
    "classic": (
        "style it as a classic version of the garment - clean, traditional, "
        "timeless lines and even proportions."
    ),
    "regular": (
        "give it a regular, relaxed-but-fitting silhouette with balanced "
        "proportions."
    ),
    "slim": (
        "give it a slim-fit, close-to-the-body tailored silhouette while "
        "keeping the garment type unmistakable."
    ),
    "oversized": (
        "give it an oversized, relaxed silhouette while still clearly "
        "remaining the selected garment type with its proper construction."
    ),
    "straight": (
        "cut it straight - a straight silhouette that runs from the shoulder "
        "to the hem without flaring."
    ),
    "a_line": (
        "cut it in an A-line - gently flaring from the chest/waist to a "
        "wider hem."
    ),
    "anarkali": (
        "make it an anarkali-style fit - fitted to the waist and flaring "
        "wide from the hip down, keeping the traditional garment type."
    ),
    "short_kurti": (
        "make it a short kurti, hip-length or slightly above, keeping the "
        "kurti silhouette and construction."
    ),
    "pathani": (
        "style it as a Pathani cut - a straight, flowing silhouette with a "
        "buttoned placket and round collar, keeping the garment type."
    ),
    "straight_fit": (
        "give it a straight fit - clean vertical lines from the waist to the "
        "hem."
    ),
    "crop": (
        "make it a cropped version of the garment - ending at or above the "
        "waist, while keeping the garment type's construction."
    ),
    "peplum": (
        "add a peplum - a short flared fabric ruffle at the waist, while "
        "keeping the garment type."
    ),
    "tunic": (
        "give it a tunic-style length - hip- to mid-thigh, keeping the "
        "selected garment type's construction."
    ),
    "collar": (
        "add a structured collar to the garment while keeping its type."
    ),
    "bodycon": (
        "make it a bodycon fit - close-fitting and fitted to every curve, "
        "while keeping the garment type."
    ),
    "maxi": (
        "make it a maxi-length garment - flowing to the ankles, keeping the "
        "garment type."
    ),
    "wrap": (
        "make it a wrap-style garment with a crossing front closure, keeping "
        "the garment type."
    ),
    "formal": (
        "style it as formal wear - crisp, tailored, dressier construction "
        "with sharp lines, while keeping the garment type unmistakable."
    ),
    "casual": (
        "style it as casual everyday wear - relaxed and comfortable while "
        "keeping the garment type unmistakable."
    ),
    "cargo": (
        "make it cargo-style with utility patch pockets, keeping the garment "
        "type."
    ),
    "bootcut": (
        "cut it bootcut - fitted through the thigh and slightly flaring from "
        "the knee to the hem."
    ),
    "baggy": (
        "make it baggy - loose, relaxed and oversized, keeping the garment "
        "type."
    ),
    "wide_leg": (
        "make it wide-leg - trouser legs that are wide and flowing from the "
        "hip down, keeping the garment type."
    ),
    "flared": (
        "flared - fitted through the hip and flaring from the knee to the " 
        "hem, keeping the garment type."
    ),
    "traditional": (
        "style it traditionally - authentic, classic traditional construction "
        "and finishing, keeping the garment type."
    ),
    "modern": (
        "style it in a modern, contemporary interpretation, keeping the "
        "garment type."
    ),
    "party": (
        "style it for festive/party wear - elegant, celebratory finishing "
        "with embellishment-friendly construction, keeping the garment type."
    ),
    "bridal": (
        "style it as bridal wear - ornate, luxurious finishing and rich "
        "detailing, keeping the garment type."
    ),
    "classic_drape": (
        "drape it classically - the traditional classic drape for the "
        "garment type."
    ),
    "open_drape": (
        "drape it in an open, casual style while keeping the garment type."
    ),
    "one_shoulder": (
        "style it with a one-shoulder silhouette - one strap over one "
        "shoulder, keeping the garment type's construction."
    ),
    "tiered": (
        "make it tiered - stacked horizontal layers of fabric, keeping the "
        "garment type."
    ),
    "empire": (
        "give it an empire waist - a high waistline just below the bust, "
        "keeping the garment type."
    ),
    "kurta_set": (
        "make it a kurta set - a kurta paired with pajama/straight trousers "
        "as a coordinated ethnic set."
    ),
    "dhoti_set": (
        "make it a dhoti set - a kurta paired with dhoti-style trousers as a "
        "traditional ethnic set."
    ),
    "ethnic_dress": (
        "make it an ethnic dress with traditional Indian styling and "
        "detailing."
    ),
    "blazer": (
        "style it as a blazer - crisp, structured and tailored with a sharp "
        "shoulder line."
    ),
    "denim": (
        "make it in denim - durable denim fabric and classic jean-style "
        "construction."
    ),
    "bomber": (
        "style it as a bomber jacket - a short, boxy fit with a front zip "
        "and elasticized cuffs and hem."
    ),
    "hooded": (
        "style it with a hood, keeping the garment type."
    ),
    "classic_tailored": (
        "make it classic and tailored - sharp, precise tailoring with clean "
        "lines."
    ),
}


def garment_type_constraint(garment_type: str) -> str:
    """Hard-constraint sentence for the selected garment type."""
    key = normalize(garment_type)
    spec = GARMENT_SPECS.get(key)
    if spec:
        return spec[0]
    label = display_name(garment_type).lower()
    return (
        f"a {label} with the unmistakable, classic {label} silhouette and "
        f"construction - it must clearly read as a {label} and nothing else."
    )


_DEV_NEGATIVE_CONSTRAINTS = (
    "generic T-shirt",
    "generic top",
    "tunic",
    "kurti",
    "western shirt",
    "t-shirt",
    "jacket",
)


def garment_negative_constraint(garment_type: str, garment_style: str = "") -> str:
    """'Avoid rendering as …' sentence for the selected garment type.

    For the 'designer' style in particular we forbid drift into a shirt / kurta /
    tunic silhouette by mixing the type's own negatives with a short set of
    developer-forbidden categories. Everything stays per-type (Blouse -> blouse;
    T-Shirt -> t-shirt), so a merchant sees 'blouse' and a developer sees the
    real forbidden list - not one giant generic negative prompt. A type's own
    name (and its own existing negatives) are never duplicated.
    """
    type_spec = GARMENT_SPECS.get(normalize(garment_type))
    negatives: list[str] = []
    if type_spec and type_spec[1]:
        negatives.extend(type_spec[1])
        if normalize(garment_style) == "designer":
            type_name = display_name(garment_type).strip().lower()
            for d in _DEV_NEGATIVE_CONSTRAINTS:
                norm = d.strip().lower()
                if norm and norm != type_name and not type_name.endswith(norm):
                    if norm not in (n.strip().lower() for n in negatives):
                        negatives.append(d)
    if not negatives:
        return ""
    return "Explicitly avoid rendering it as any of: " + ", ".join(negatives) + "."


def style_constraint(garment_type: str, garment_style: str) -> str:
    """Style modifier sentence - style acts on the garment, never replaces it."""
    key = normalize(garment_style)
    style_texts = STYLE_SPECS.get(key)
    label = display_name(garment_type).strip().lower() or "garment"
    if style_texts:
        if isinstance(style_texts, str):
            main, forbidden = style_texts, ()
        else:
            main = style_texts[0]
            forbidden = style_texts[1] if len(style_texts) > 1 else ()
        text = (
            f"The selected style '{display_name(garment_style)}' means: {main} "
            f"Apply it to the {label} as finishing details only - it must never "
            f"change the garment category away from a {label}."
        )
        if forbidden:
            text += " Explicitly do not turn the style feature into: " + ", ".join(
                forbidden
            ) + "."
        return text
    return (
        f"The selected style '{display_name(garment_style)}' modifies the "
        f"{label} (neckline, fit, sleeves or detailing) and must NEVER change "
        f"the garment category - keep it a {label} throughout."
    )


def priority_rule(garment_type: str) -> str:
    """Dominance statement: type > reference > style > fabric > fit (type wins)."""
    label = display_name(garment_type).strip().lower() or "garment"
    return (
        f"The selected garment type is the dominant HARD CONSTRAINT: it "
        f"controls the complete silhouette and construction. What is generated "
        f"must remain a {label} from start to finish, so a viewer can name the "
        f"correct garment category from the silhouette alone, before reading "
        f"any fabric pattern or style detail. Priority: garment type, then the "
        f"garment-reference image, then style, then fabric. The style, the "
        f"reported fabric details and the body fit only refine the {label} - "
        f"they must NEVER override, replace, re-categorise or genericize it. "
        f"If the style or the reference fabric conflicts with the type, the "
        f"{label} type wins every time and the garment stays a {label}."
    )


def constraint_flags(garment_type: str, garment_style: str) -> dict:
    """Audit flags: whether a tailored type/style constraint applied.

    - ``garment_type_constraint``: True whenever a garment type was given
      (a hard-constraint sentence is always injected).
    - ``style_constraint``: True only when a *known* style spec was found and
      injected (unknown styles fall back to a generic modifier sentence).
    """
    return {
        "garment_type_constraint": bool(garment_type),
        "style_constraint": bool(
            garment_style
            and normalize(garment_style) in STYLE_SPECS
        ),
    }