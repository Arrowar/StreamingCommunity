from pathlib import Path
import shutil
import sys


DESTINATION_MAP = {
    "Movie": Path("/app/VideoShare/movies"),
    "Serie": Path("/app/VideoShare/tv"),
    "Anime": Path("/app/VideoShare/anime"),
}


def find_category_index(source_path: Path) -> tuple[str, int]:
    source_parts = source_path.parts

    for category in DESTINATION_MAP:
        if category in source_parts:
            return category, source_parts.index(category)

    supported_categories = ", ".join(DESTINATION_MAP)
    raise ValueError(
        f"Categoria non trovata nel path '{source_path}'. Attese: {supported_categories}"
    )


def resolve_destination(source_path: Path) -> Path:
    category, category_index = find_category_index(source_path)
    relative_parts = source_path.parts[category_index + 1 :]
    if not relative_parts:
        raise ValueError(f"Nessun percorso relativo dopo la categoria '{category}'")

    return DESTINATION_MAP[category].joinpath(*relative_parts)


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Uso: end.py <download_path>")

    source_path = Path(sys.argv[1]).expanduser()
    if not source_path.exists() or not source_path.is_file():
        raise FileNotFoundError(f"File sorgente non trovato: {source_path}")

    destination_path = resolve_destination(source_path)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, destination_path)
    source_path.unlink()

    print(f"Moved '{source_path}' -> '{destination_path}'")


if __name__ == "__main__":
    main()
