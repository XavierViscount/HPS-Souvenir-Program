"""
bouquet_generator.py
────────────────────
Core image-processing module for the Fundraising Flower Bouquet Generator.
Generates a complete souvenir card (2880 × 1728) with:
  • Circular bouquet composite with dynamic 1–10 flower slot layouts
  • Automatic variant selection:
      - 1 to 3 flowers  → '1_to_3.png'
      - 4 to 10 flowers → directional 'left.png', 'middle.png', 'right.png' (or 'all_same.png')
  • Red ribbon bow overlay over the bouquet tie point
  • Donor ID & Total Flower count badges
  • Flower selection checklist marked next to each flower name
"""

import math
import os
from collections import Counter
from PIL import Image, ImageDraw, ImageFont

# ─── Directory Paths ──────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
FLOWERS_DIR = os.path.join(ASSETS_DIR, "flowers")
CARD_PATH = os.path.join(ASSETS_DIR, "background", "souvenir_card.png")
RIBBON_PATH = os.path.join(ASSETS_DIR, "ribbon", "ribbon.png")
THABYAY_PATH = os.path.join(ASSETS_DIR, "thabyay.png")

# Premade single-type bouquet images  (PremadeFlowers/<key>/1.PNG … 10.PNG)
PREMADE_FLOWERS_DIR = os.path.join(BASE_DIR, "PremadeFlowers")

# For most folders: sorted filenames ascending  → index 0 = 1 flower, index 9 = 10 flowers.
# thazin was photographed in reverse (most flowers first), so we sort descending.
# kankaw folder is capitalised on disk; key is lowercase – handled in the resolver.
_PREMADE_SORT_REVERSE: set[str] = {"thazin"}

# Windows Myanmar Unicode Font
FONT_PATH = r"C:\Windows\Fonts\mmrtextb.ttf"
if not os.path.exists(FONT_PATH):
    FONT_PATH = r"C:\Windows\Fonts\mmrtext.ttf"

# ─── Flower Catalogue Mapping ─────────────────────────────────────────────────

FLOWER_CATALOGUE = {
    1:  {"key": "rose",      "name": "နှင်းဆီ",    "full_name": "နှင်းဆီပန်း",    "emoji": "🌹"},
    2:  {"key": "thazin",    "name": "သဇင်",      "full_name": "သဇင်ပန်း",      "emoji": "🌾"},
    3:  {"key": "orchid",    "name": "သစ်ခွ",     "full_name": "သစ်ခွပန်း",     "emoji": "🌺"},
    4:  {"key": "sabal",     "name": "စံပယ်",      "full_name": "စံပယ်ပန်း",      "emoji": "🪷"},
    5:  {"key": "padouk",    "name": "ပိတောက်",    "full_name": "ပိတောက်ပန်း",    "emoji": "🏵️"},
    6:  {"key": "cherry",    "name": "ချယ်ရီ",     "full_name": "ချယ်ရီပန်း",     "emoji": "🌸"},
    7:  {"key": "lavender",  "name": "လာဗင်ဒါ",   "full_name": "လာဗင်ဒါပန်း",   "emoji": "🪻"},
    8:  {"key": "kankaw",    "name": "ကံ့ကော်",    "full_name": "ကံ့ကော်ပန်း",    "emoji": "🌼"},
    9:  {"key": "sunflower", "name": "နေကြာ",     "full_name": "နေကြာပန်း",     "emoji": "🌻"},
    10: {"key": "tulip",     "name": "ကျူးလစ်",    "full_name": "ကျူးလစ်ပန်း",    "emoji": "🌷"},
}

KEY_TO_ID = {v["key"]: k for k, v in FLOWER_CATALOGUE.items()}

# Checklist label coordinates on the card
CHECKLIST_COORDS = {
    "rose":      (1730, 910),
    "thazin":    (1730, 1045),
    "orchid":    (1730, 1190),

    "sabal":     (2220, 910),
    "padouk":    (2220, 1045),
    "cherry":    (2220, 1190),
    "lavender":  (2230, 1335),

    "kankaw":    (2670, 910),
    "sunflower": (2670, 1045),
    "tulip":     (2670, 1190),
}

BURMESE_DIGITS = str.maketrans("0123456789", "၀၁၂၃၄၅၆၇၈၉")


def to_burmese_num(n: int | str) -> str:
    """Convert digits to Myanmar Unicode digits."""
    return str(n).translate(BURMESE_DIGITS)


def _fit_font(text: str, max_width: int, max_size: int, min_size: int = 30) -> ImageFont.FreeTypeFont:
    """Return the largest available font size that fits the target width."""
    for size in range(max_size, min_size - 1, -1):
        font = ImageFont.truetype(FONT_PATH, size)
        if font.getlength(text) <= max_width:
            return font
    return ImageFont.truetype(FONT_PATH, min_size)


# ─── Flower Slot Layouts (1 to 10 flowers) ───────────────────────────────────
# Center of framed circle: (644, 850)
# Ribbon tie center: x=644; y moves lower as the bouquet gets fuller.
# Slots are listed in rendering order (back row to front row)

SLOT_CONFIGS: dict[int, list[dict]] = {
    1: [
        {"h": 860, "rot": 0, "pos": "middle"},
    ],
    2: [
        {"h": 830, "rot": -10, "pos": "left"},
        {"h": 830, "rot":  10, "pos": "right"},
    ],
    3: [
        {"h": 820, "rot": -14, "pos": "left"},
        {"h": 840, "rot":   0, "pos": "middle"},
        {"h": 820, "rot":  14, "pos": "right"},
    ],
    4: [
        # Back (2)
        {"h": 840, "rot": -14, "pos": "left"},
        {"h": 840, "rot":  14, "pos": "right"},
        # Front (2)
        {"h": 770, "rot":  -6, "pos": "left"},
        {"h": 770, "rot":   6, "pos": "right"},
    ],
    5: [
        # Back (3)
        {"h": 850, "rot": -18, "pos": "left"},
        {"h": 860, "rot":   0, "pos": "middle"},
        {"h": 850, "rot":  18, "pos": "right"},
        # Front (2)
        {"h": 770, "rot":  -8, "pos": "left"},
        {"h": 770, "rot":   8, "pos": "right"},
    ],
    6: [
        # Back (3)
        {"h": 860, "rot": -20, "pos": "left"},
        {"h": 870, "rot":   0, "pos": "middle"},
        {"h": 860, "rot":  20, "pos": "right"},
        # Front (3)
        {"h": 770, "rot":  -9, "pos": "left"},
        {"h": 780, "rot":   0, "pos": "middle"},
        {"h": 770, "rot":   9, "pos": "right"},
    ],
    7: [
        # Back (3)
        {"h": 865, "rot": -22, "pos": "left"},
        {"h": 875, "rot":   0, "pos": "middle"},
        {"h": 865, "rot":  22, "pos": "right"},
        # Mid (2)
        {"h": 800, "rot": -10, "pos": "left"},
        {"h": 800, "rot":  10, "pos": "right"},
        # Front (2)
        {"h": 750, "rot":  -5, "pos": "left"},
        {"h": 750, "rot":   5, "pos": "right"},
    ],
    8: [
        # Back (3)
        {"h": 870, "rot": -23, "pos": "left"},
        {"h": 880, "rot":   0, "pos": "middle"},
        {"h": 870, "rot":  23, "pos": "right"},
        # Mid (3)
        {"h": 810, "rot": -12, "pos": "left"},
        {"h": 815, "rot":   0, "pos": "middle"},
        {"h": 810, "rot":  12, "pos": "right"},
        # Front (2)
        {"h": 750, "rot":  -6, "pos": "left"},
        {"h": 750, "rot":   6, "pos": "right"},
    ],
    9: [
        # Back (3)
        {"h": 870, "rot": -25, "pos": "left"},
        {"h": 880, "rot":   0, "pos": "middle"},
        {"h": 870, "rot":  25, "pos": "right"},
        # Mid (3)
        {"h": 815, "rot": -13, "pos": "left"},
        {"h": 820, "rot":   0, "pos": "middle"},
        {"h": 815, "rot":  13, "pos": "right"},
        # Front (3)
        {"h": 750, "rot":  -6, "pos": "left"},
        {"h": 755, "rot":   0, "pos": "middle"},
        {"h": 750, "rot":   6, "pos": "right"},
    ],
    10: [
        # Back (3)
        {"h": 870, "rot": -25, "pos": "left"},
        {"h": 880, "rot":   0, "pos": "middle"},
        {"h": 870, "rot":  25, "pos": "right"},
        # Mid (4)
        {"h": 820, "rot": -16, "pos": "left"},
        {"h": 810, "rot":  -6, "pos": "left"},
        {"h": 810, "rot":   6, "pos": "right"},
        {"h": 820, "rot":  16, "pos": "right"},
        # Front (3)
        {"h": 740, "rot":  -8, "pos": "left"},
        {"h": 750, "rot":   0, "pos": "middle"},
        {"h": 740, "rot":   8, "pos": "right"},
    ],
}

ARRANGEMENT_STYLES = {"balanced": 1.0, "compact": 0.65, "fan": 1.35}


# ─── Image Helpers ────────────────────────────────────────────────────────────

def get_flower_variant_path(flower_key: str, total_count: int, position: str) -> str:
    """
    Resolve the sprite path based on total count and slot position.
      - total_count <= 3  → '1_to_3.png'
      - total_count >= 4  → '<position>.png' (e.g. left, middle, right)
                            or 'all_same.png'
    """
    fdir = os.path.join(FLOWERS_DIR, flower_key)
    if not os.path.isdir(fdir):
        raise FileNotFoundError(f"Flower directory not found: {fdir}")

    # Phase 1: 1 to 3 flowers
    if total_count <= 3:
        p = os.path.join(fdir, "1_to_3.png")
        if os.path.exists(p):
            return p

    # Phase 2: 4 to 10 flowers
    pos_file = os.path.join(fdir, f"{position}.png")
    if os.path.exists(pos_file):
        return pos_file

    same_file = os.path.join(fdir, "all_same.png")
    if os.path.exists(same_file):
        return same_file

    # Fallbacks
    for name in ["1_to_3.png", "middle.png", "all_same.png"]:
        fallback = os.path.join(fdir, name)
        if os.path.exists(fallback):
            return fallback

    for fname in os.listdir(fdir):
        if fname.lower().endswith(".png"):
            return os.path.join(fdir, fname)

    raise FileNotFoundError(f"No valid PNG image found for flower '{flower_key}' in {fdir}")


def _balance_flowers_for_slots(
    flower_keys: list[str], total_count: int, slots: list[dict]
) -> list[str]:
    """Assign similarly sized flowers to opposite sides of the bouquet."""
    weights: dict[str, float] = {}
    for flower_key in set(flower_keys):
        sprite_path = get_flower_variant_path(flower_key, total_count, "middle")
        with Image.open(sprite_path) as sprite:
            alpha = sprite.convert("RGBA").getchannel("A")
            visible = alpha.getbbox()
            if visible:
                alpha = alpha.crop(visible)
                weights[flower_key] = sum(alpha.histogram()[1:]) / alpha.height**2
            else:
                weights[flower_key] = 0.0

    assignments: list[str | None] = [None] * len(slots)
    remaining = sorted(flower_keys, key=lambda key: weights[key], reverse=True)
    middle_indices = [i for i, slot in enumerate(slots) if slot["pos"] == "middle"]
    side_pairs: dict[tuple[int, int], dict[str, int]] = {}

    for index, slot in enumerate(slots):
        if slot["pos"] != "middle":
            pair_key = (slot["h"], abs(slot["rot"]))
            side_pairs.setdefault(pair_key, {})[slot["pos"]] = index

    for index in sorted(middle_indices, key=lambda i: slots[i]["h"], reverse=True):
        assignments[index] = remaining.pop(0)

    side_weights = {"left": 0.0, "right": 0.0}
    for (height, _), pair in sorted(side_pairs.items(), reverse=True):
        first, second = remaining.pop(0), remaining.pop(0)
        heavier, lighter = sorted((first, second), key=lambda key: weights[key], reverse=True)
        if side_weights["left"] <= side_weights["right"]:
            assignments[pair["left"]] = heavier
            assignments[pair["right"]] = lighter
        else:
            assignments[pair["left"]] = lighter
            assignments[pair["right"]] = heavier
        side_weights["left"] += weights[assignments[pair["left"]]] * height**2
        side_weights["right"] += weights[assignments[pair["right"]]] * height**2

    return [flower_key for flower_key in assignments if flower_key is not None]


def place_flower_by_stem(
    canvas: Image.Image,
    flower: Image.Image,
    stem_target_x: int,
    stem_target_y: int,
    target_h: int,
    angle: float,
) -> None:
    """
    Place *flower* onto *canvas* by anchoring its stem base at (stem_target_x, stem_target_y),
    scaled to *target_h* and rotated clockwise by *angle* degrees.
    """
    bbox = flower.getbbox()
    if not bbox:
        return
    cropped = flower.crop(bbox)

    orig_w, orig_h = cropped.size
    ratio = target_h / orig_h
    new_w = max(1, int(orig_w * ratio))
    new_h = target_h
    scaled = cropped.resize((new_w, new_h), Image.LANCZOS)

    # Local coordinates of stem base in the scaled image (bottom center)
    stem_local_x = new_w / 2.0
    stem_local_y = float(new_h)

    if angle != 0:
        # PIL rotate is counter-clockwise, so negate for clockwise
        rotated = scaled.rotate(-angle, expand=True, resample=Image.BICUBIC)

        rad = math.radians(angle)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)

        cx_orig = new_w / 2.0
        cy_orig = new_h / 2.0

        rx = stem_local_x - cx_orig
        ry = stem_local_y - cy_orig

        rx_rot = rx * cos_a - ry * sin_a
        ry_rot = rx * sin_a + ry * cos_a

        cx_rot = rotated.width / 2.0
        cy_rot = rotated.height / 2.0

        stem_rot_x = cx_rot + rx_rot
        stem_rot_y = cy_rot + ry_rot
    else:
        rotated = scaled
        stem_rot_x = stem_local_x
        stem_rot_y = stem_local_y

    paste_x = int(stem_target_x - stem_rot_x)
    paste_y = int(stem_target_y - stem_rot_y)

    canvas.alpha_composite(rotated, (paste_x, paste_y))


# ─── Public API ───────────────────────────────────────────────────────────────

def generate_bouquet(
    selected_flowers: list[int | str],
    output_path: str | None = None,
    donor_id: str = "#1001",
    arrangement: str = "balanced",
):
    """
    Generate the complete souvenir card image with the flower bouquet, ribbon,
    and text annotations.

    Parameters
    ----------
    selected_flowers : list[int | str]
        List of flower IDs (1-10) or keys ('rose', 'tulip', etc.).
        Minimum 1, maximum 10.
    output_path : str | None
        Target file path for the resulting PNG image. If None, returns io.BytesIO.
    donor_id : str
        Donor display text / ID to place in the card's 'ID :' badge.
    arrangement : str
        Flower spread preset: balanced, compact, or fan.

    Returns
    -------
    str | io.BytesIO
        The absolute path to the saved image, or a BytesIO object containing the PNG data.
    """
    if not selected_flowers:
        raise ValueError("selected_flowers must contain at least one flower.")
    if not isinstance(arrangement, str) or arrangement not in ARRANGEMENT_STYLES:
        raise ValueError(f"Unknown arrangement '{arrangement}'.")

    # Normalise all items to flower keys
    flower_keys: list[str] = []
    for item in selected_flowers:
        if isinstance(item, int):
            if item not in FLOWER_CATALOGUE:
                raise ValueError(f"Invalid flower ID '{item}'. Valid IDs are 1 to 10.")
            flower_keys.append(FLOWER_CATALOGUE[item]["key"])
        elif isinstance(item, str):
            k = item.lower()
            if k in KEY_TO_ID:
                flower_keys.append(k)
            else:
                raise ValueError(f"Unknown flower key '{item}'.")
        else:
            raise TypeError(f"Flower must be int or str, got {type(item)}.")

    # Cap at 10
    flower_keys = flower_keys[:10]
    total_count = len(flower_keys)
    stem_y = 1160 + (total_count - 1) * 7
    bow_y = stem_y - 55

    # ── 1. Load Background Card Canvas ───────────────────────────────────────
    if not os.path.exists(CARD_PATH):
        raise FileNotFoundError(f"Background card template not found at {CARD_PATH}")
    card = Image.open(CARD_PATH).convert("RGBA")

    # ── 2. Render Bouquet Layer by Layer ─────────────────────────────────────
    spread = ARRANGEMENT_STYLES[arrangement]
    slots = [
        {**slot, "rot": slot["rot"] * spread}
        for slot in SLOT_CONFIGS.get(total_count, SLOT_CONFIGS[10])
    ]
    flowers_for_slots = _balance_flowers_for_slots(flower_keys, total_count, slots)

    thabyay_img = Image.open(THABYAY_PATH).convert("RGBA").transpose(
        Image.Transpose.FLIP_LEFT_RIGHT
    )
    place_flower_by_stem(
        canvas=card,
        flower=thabyay_img,
        stem_target_x=644,
        stem_target_y=stem_y,
        target_h=830,
        angle=0,
    )

    for i, fkey in enumerate(flowers_for_slots):
        slot = slots[i]
        variant_path = get_flower_variant_path(fkey, total_count, slot["pos"])
        flower_img = Image.open(variant_path).convert("RGBA")
        place_flower_by_stem(
            canvas=card,
            flower=flower_img,
            stem_target_x=644,
            stem_target_y=stem_y,
            target_h=slot["h"],
            angle=slot["rot"],
        )

    # ── 3. Overlay Ribbon Bow over stems ─────────────────────────────────────
    if os.path.exists(RIBBON_PATH):
        ribbon = Image.open(RIBBON_PATH).convert("RGBA")
        r_bbox = ribbon.getbbox()
        if r_bbox:
            ribbon_crop = ribbon.crop(r_bbox)
            r_w = 400 + (total_count - 1) * 25
            r_h = int(ribbon_crop.height * r_w / ribbon_crop.width)
            ribbon_scaled = ribbon_crop.resize((r_w, r_h), Image.LANCZOS)
            card.alpha_composite(ribbon_scaled, (644 - r_w // 2, bow_y - r_h // 2))

    # ── 4. Draw Badges & Checklist Annotations ──────────────────────────────
    draw = ImageDraw.Draw(card)

    donor_text = str(donor_id)
    font_badge = _fit_font(donor_text, max_width=470, max_size=46)
    font_total = _fit_font("၁၀ ပွင့်", max_width=130, max_size=38)
    font_check = ImageFont.truetype(FONT_PATH, 42)

    # Center dynamic values within the blank portions of the printed badges.
    donor_bbox = draw.textbbox((0, 0), donor_text, font=font_badge, stroke_width=1)
    donor_position = (
        1540 - donor_bbox[0],
        763 - (donor_bbox[1] + donor_bbox[3]) / 2,
    )
    draw.text(
        donor_position, donor_text, font=font_badge, fill=(255, 255, 255, 255),
        stroke_width=1, stroke_fill=(100, 20, 30, 150),
    )

    total_str = f"{to_burmese_num(total_count + 1)} ပွင့်"
    total_bbox = draw.textbbox((0, 0), total_str, font=font_total, stroke_width=1)
    total_position = (
        2515 - (total_bbox[0] + total_bbox[2]) / 2,
        763 - (total_bbox[1] + total_bbox[3]) / 2,
    )
    draw.text(
        total_position, total_str, font=font_total, fill=(255, 255, 255, 255),
        stroke_width=1, stroke_fill=(100, 20, 30, 150),
    )

    # Checklist next to flower names
    counts = Counter(flower_keys)
    for fkey, coord in CHECKLIST_COORDS.items():
        cnt = counts.get(fkey, 0)
        if cnt > 0:
            mark = f"{to_burmese_num(cnt)} ပွင့်"
            mark_bbox = draw.textbbox((0, 0), mark, font=font_check, stroke_width=1)
            mark_position = (
                coord[0] - mark_bbox[0],
                coord[1] - (mark_bbox[1] + mark_bbox[3]) / 2,
            )
            draw.text(
                mark_position, mark, font=font_check, fill=(184, 37, 54, 255),
                stroke_width=1, stroke_fill=(110, 35, 48, 110),
            )
        else:
            dash_bbox = draw.textbbox((0, 0), "—", font=font_check)
            dash_position = (
                coord[0] - dash_bbox[0],
                coord[1] - (dash_bbox[1] + dash_bbox[3]) / 2,
            )
            draw.text(dash_position, "—", font=font_check, fill=(190, 150, 160, 200))

    # ── 5. Save Output Image ─────────────────────────────────────────────────
    if output_path:
        output_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        card.convert("RGB").save(output_path, format="PNG", optimize=True)
        print(f"[DONE] Souvenir card saved -> {output_path}")
        return output_path
    else:
        import io
        bio = io.BytesIO()
        card.convert("RGB").save(bio, format="PNG", optimize=True)
        bio.seek(0)
        return bio


# ─── Premade Bouquet Resolver & Single-Type Generator ────────────────────────

def resolve_premade_path(flower_key: str, quantity: int) -> str:
    """
    Return the absolute path of the premade bouquet image for *flower_key*
    at *quantity* (1–10).

    Naming strategies handled automatically:
    ─────────────────────────────────────────
    Strategy A – numeric names (rose, sabal, tulip):
        PremadeFlowers/<key>/1.PNG, 2.PNG … 10.PNG
        → open directly by number.

    Strategy B – IMG-named, sorted ascending = 1..N flowers:
        PremadeFlowers/<key>/IMG_2750.PNG … IMG_2762.PNG  (most folders)
        → sort filenames ascending; index (quantity-1) is the target.

    Strategy C – IMG-named, sorted DESCENDING = 1..N flowers (thazin):
        Sorted descending; index (quantity-1) is the target.

    The folder name on disk may be mixed-case (KanKaw).  A case-insensitive
    search is performed so the caller can always pass a lowercase key.

    Parameters
    ----------
    flower_key : str
        Lowercase flower key, e.g. 'rose', 'kankaw', 'thazin'.
    quantity : int
        Number of flowers (1–10).

    Returns
    -------
    str
        Absolute path to the matching PNG.

    Raises
    ------
    FileNotFoundError
        If the folder doesn't exist or has fewer images than requested.
    """
    # ── Find folder (case-insensitive) ───────────────────────────────────────
    if not os.path.isdir(PREMADE_FLOWERS_DIR):
        raise FileNotFoundError(f"PremadeFlowers directory not found: {PREMADE_FLOWERS_DIR}")

    matched_folder: str | None = None
    for entry in os.listdir(PREMADE_FLOWERS_DIR):
        if entry.lower() == flower_key.lower():
            matched_folder = os.path.join(PREMADE_FLOWERS_DIR, entry)
            break

    if matched_folder is None:
        raise FileNotFoundError(
            f"No premade folder found for flower '{flower_key}' "
            f"in {PREMADE_FLOWERS_DIR}"
        )

    # ── Strategy A: numeric filenames ────────────────────────────────────────
    for ext in (".PNG", ".png", ".jpg", ".jpeg"):
        numeric_path = os.path.join(matched_folder, f"{quantity}{ext}")
        if os.path.isfile(numeric_path):
            return numeric_path

    # ── Strategy B / C: IMG-named files ──────────────────────────────────────
    image_exts = {".png", ".jpg", ".jpeg"}
    img_files = sorted(
        [f for f in os.listdir(matched_folder)
         if os.path.splitext(f)[1].lower() in image_exts],
        reverse=(flower_key.lower() in _PREMADE_SORT_REVERSE),
    )

    if not img_files:
        raise FileNotFoundError(
            f"No images found in premade folder: {matched_folder}"
        )

    # Clamp: if the folder has fewer images than MAX (e.g. thazin has 9),
    # return the last available image for out-of-range quantities.
    index = min(quantity - 1, len(img_files) - 1)
    return os.path.join(matched_folder, img_files[index])


def generate_single_bouquet(
    flower_id: int,
    quantity: int,
    output_path: str | None = None,
    donor_id: str = "#1001",
):
    """
    Generate a souvenir card for the Single-type bot.

    Instead of compositing individual flower sprites, it loads the premade
    bouquet image from ``PremadeFlowers/<key>/<quantity>.PNG`` and places it
    on the card exactly where the dynamic bouquet sits — anchored at the stem
    base point (x=644) so it lines up with the ribbon and card frame.

    The checklist, donor-ID badge, and total-count badge are drawn the same
    way as ``generate_bouquet()``.

    Parameters
    ----------
    flower_id : int
        Flower catalogue ID (1–10).
    quantity : int
        Number of flowers ordered (1–10).
    output_path : str
        Destination PNG path.
    donor_id : str
        Student/donor ID to print on the card.

    Returns
    -------
    str
        Absolute path of the saved image.
    """
    if flower_id not in FLOWER_CATALOGUE:
        raise ValueError(f"Invalid flower_id '{flower_id}'. Valid IDs are 1–10.")
    if not 1 <= quantity <= 10:
        raise ValueError(f"quantity must be between 1 and 10, got {quantity}.")

    flower_info = FLOWER_CATALOGUE[flower_id]
    flower_key  = flower_info["key"]

    # ── 1. Load card background ───────────────────────────────────────────────
    if not os.path.exists(CARD_PATH):
        raise FileNotFoundError(f"Background card not found: {CARD_PATH}")
    card = Image.open(CARD_PATH).convert("RGBA")

    # ── 2. Resolve & place premade bouquet image ──────────────────────────────
    premade_path = resolve_premade_path(flower_key, quantity)
    bouquet_img  = Image.open(premade_path).convert("RGBA")

    # The premade images are 2048×2048 square photos.
    # We place them by stem-base, same anchor the mixed bot uses:
    #   stem_target_x = 644  (centre of the circular frame on the card)
    #   stem_target_y = 1160 + (quantity-1)*7  (rises slightly with more flowers)
    stem_x = 644
    stem_y = 1160 + (quantity - 1) * 7

    # Scale to match the height the mixed-bot uses for its biggest single stem
    # (≈870 px for the back-row flower). The premade image fills the full frame
    # so we use a slightly taller height to ensure full bouquet visibility.
    target_h = 860 + (quantity - 1) * 3   # 860 (qty=1) → 887 (qty=10)

    place_flower_by_stem(
        canvas=card,
        flower=bouquet_img,
        stem_target_x=stem_x,
        stem_target_y=stem_y,
        target_h=target_h,
        angle=0,
    )

    # ── 3. Ribbon bow ─────────────────────────────────────────────────────────
    bow_y = stem_y - 55
    if os.path.exists(RIBBON_PATH):
        ribbon = Image.open(RIBBON_PATH).convert("RGBA")
        r_bbox = ribbon.getbbox()
        if r_bbox:
            ribbon_crop = ribbon.crop(r_bbox)
            r_w = 400 + (quantity - 1) * 25
            r_h = int(ribbon_crop.height * r_w / ribbon_crop.width)
            ribbon_scaled = ribbon_crop.resize((r_w, r_h), Image.LANCZOS)
            card.alpha_composite(ribbon_scaled, (stem_x - r_w // 2, bow_y - r_h // 2))

    # ── 4. Text badges & checklist ────────────────────────────────────────────
    draw = ImageDraw.Draw(card)

    font_badge = _fit_font(str(donor_id), max_width=470, max_size=46)
    font_total = _fit_font("၁၀ ပွင့်", max_width=130, max_size=38)
    font_check = ImageFont.truetype(FONT_PATH, 42)

    # Donor ID badge
    donor_text = str(donor_id)
    donor_bbox = draw.textbbox((0, 0), donor_text, font=font_badge, stroke_width=1)
    draw.text(
        (1540 - donor_bbox[0], 763 - (donor_bbox[1] + donor_bbox[3]) / 2),
        donor_text,
        font=font_badge,
        fill=(255, 255, 255, 255),
        stroke_width=1,
        stroke_fill=(100, 20, 30, 150),
    )

    # Total flower count badge
    total_str   = f"{to_burmese_num(quantity)} ပွင့်"
    total_bbox  = draw.textbbox((0, 0), total_str, font=font_total, stroke_width=1)
    draw.text(
        (2515 - (total_bbox[0] + total_bbox[2]) / 2,
         763  - (total_bbox[1] + total_bbox[3]) / 2),
        total_str,
        font=font_total,
        fill=(255, 255, 255, 255),
        stroke_width=1,
        stroke_fill=(100, 20, 30, 150),
    )

    # Checklist – only this flower gets a count mark; all others get a dash
    for fkey, coord in CHECKLIST_COORDS.items():
        if fkey == flower_key:
            mark = f"{to_burmese_num(quantity)} ပွင့်"
            mark_bbox = draw.textbbox((0, 0), mark, font=font_check, stroke_width=1)
            draw.text(
                (coord[0] - mark_bbox[0],
                 coord[1] - (mark_bbox[1] + mark_bbox[3]) / 2),
                mark,
                font=font_check,
                fill=(184, 37, 54, 255),
                stroke_width=1,
                stroke_fill=(110, 35, 48, 110),
            )
        else:
            dash_bbox = draw.textbbox((0, 0), "—", font=font_check)
            draw.text(
                (coord[0] - dash_bbox[0],
                 coord[1] - (dash_bbox[1] + dash_bbox[3]) / 2),
                "—",
                font=font_check,
                fill=(190, 150, 160, 200),
            )

    # ── 5. Save ───────────────────────────────────────────────────────────────
    if output_path:
        output_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        card.convert("RGB").save(output_path, format="PNG", optimize=True)
        print(f"[DONE] Single souvenir card saved -> {output_path}")
        return output_path
    else:
        import io
        bio = io.BytesIO()
        card.convert("RGB").save(bio, format="PNG", optimize=True)
        bio.seek(0)
        return bio
