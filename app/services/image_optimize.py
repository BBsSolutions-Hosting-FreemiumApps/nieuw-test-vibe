import os

from PIL import Image

from app.config import get_settings


def optimize_image(source_path: str, media_dir: str) -> str:
    """Resize naar max. breedte en converteer naar geoptimaliseerd WebP."""
    max_width = get_settings().image_max_width
    out_rel = os.path.splitext(source_path)[0] + "_opt.webp"
    out_abs = os.path.join(media_dir, out_rel)
    os.makedirs(os.path.dirname(out_abs), exist_ok=True)

    with Image.open(os.path.join(media_dir, source_path)) as img:
        img = img.convert("RGB")
        if img.width > max_width:
            height = int(img.height * max_width / img.width)
            img = img.resize((max_width, height), Image.LANCZOS)
        img.save(out_abs, "WEBP", quality=82)
    return out_rel
