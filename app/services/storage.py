import os


def ensure_media_dir(media_dir: str) -> None:
    os.makedirs(media_dir, exist_ok=True)


def save_upload(media_dir: str, subdir: str, filename: str, data: bytes) -> str:
    ensure_media_dir(media_dir)
    folder = os.path.join(media_dir, subdir)
    os.makedirs(folder, exist_ok=True)
    safe = os.path.basename(filename) or "bestand"
    path = os.path.join(folder, safe)
    with open(path, "wb") as f:
        f.write(data)
    return os.path.join(subdir, safe)
