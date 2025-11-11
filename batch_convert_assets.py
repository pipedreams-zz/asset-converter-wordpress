#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import re
import unicodedata
from pathlib import Path
from typing import Iterable, Tuple, Dict, Optional

try:
    from PIL import Image, ImageOps
except ImportError:
    print("Fehler: Pillow ist nicht installiert. Bitte mit `pip install Pillow` nachinstallieren.")
    sys.exit(1)

# Increase decompression bomb limit for large images (e.g., high-res scans)
# Default: ~89 MP, New: ~300 MP (sufficient for most legitimate photos)
Image.MAX_IMAGE_PIXELS = 300_000_000

# Optional: Load AVIF support (if installed)
try:
    import pillow_avif  # noqa: F401
    AVIF_AVAILABLE = True
except Exception:
    AVIF_AVAILABLE = False

# PDF support via PyMuPDF
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except Exception:
    PYMUPDF_AVAILABLE = False


# ------------------------------
# Utility: WordPress-friendly slug creation
# ------------------------------
UMLAUT_MAP = {
    "ä": "ae", "ö": "oe", "ü": "ue",
    "Ä": "ae", "Ö": "oe", "Ü": "ue",
    "ß": "ss",
}

def wp_slugify(name: str) -> str:
    """Convert filename to WordPress-friendly slug"""
    base = name
    # Replace umlauts/ß
    for k, v in UMLAUT_MAP.items():
        base = base.replace(k, v)
    # Unicode normalization (remove diacritics)
    base = unicodedata.normalize("NFKD", base)
    base = "".join(c for c in base if not unicodedata.combining(c))
    # Lowercase
    base = base.lower()
    # Convert non-alphanumeric characters to hyphens
    base = re.sub(r"[^a-z0-9]+", "-", base)
    # Reduce multiple hyphens
    base = re.sub(r"-{2,}", "-", base)
    # Trim edge hyphens
    base = base.strip("-")
    # Fallback
    return base or "datei"

def normalize_prefix(prefix: str) -> str:
    """
    Normalize prefix: lowercase, alphanumeric only.
    Automatically adds hyphen at the end if not present.
    """
    if not prefix:
        return ""
    # Keep lowercase and alphanumeric characters only
    normalized = re.sub(r"[^a-z0-9]+", "", prefix.lower())
    # Add hyphen at the end
    if normalized and not normalized.endswith("-"):
        normalized += "-"
    return normalized

def ensure_prefix(slug: str, prefix: str) -> str:
    """
    Check if slug already starts with prefix.
    If not, prepend the prefix.
    """
    if not prefix:
        return slug
    # Prefix without hyphen for comparison
    prefix_base = prefix.rstrip("-")
    # Check if slug already starts with prefix (with or without hyphen)
    if slug.startswith(prefix) or slug.startswith(prefix_base):
        return slug
    # Add prefix
    return f"{prefix}{slug}"


# ------------------------------
# Conversion
# ------------------------------
SUPPORTED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif"}
SUPPORTED_PDF_EXTS = {".pdf"}

def ask(prompt: str, default: Optional[str] = None) -> str:
    s = f"{prompt}"
    if default is not None:
        s += f" [{default}]"
    s += ": "
    val = input(s).strip()
    return val or (default if default is not None else "")

def parse_ext_list(s: str) -> Tuple[str, ...]:
    items = [x.strip().lower().lstrip(".") for x in s.split(",") if x.strip()]
    return tuple(f".{x}" for x in items)

def ensure_output_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def compute_new_size(img: Image.Image, target_width: int) -> Tuple[int, int]:
    w, h = img.size
    if w <= target_width:
        # Don't upscale - keep original size
        return w, h
    ratio = target_width / float(w)
    return target_width, max(1, int(round(h * ratio)))

def load_image_fix_orientation(path: Path) -> Image.Image:
    im = Image.open(path)
    try:
        im = ImageOps.exif_transpose(im)
    except Exception:
        pass
    return im

def pil_mode_for_format(im: Image.Image, fmt: str, force_white_bg: bool = False) -> Image.Image:
    """
    Convert image mode for target format.
    If force_white_bg is True, always flatten transparency to white background.
    """
    # For web formats, sRGB/RGB is usually appropriate (no CMYK)
    if fmt in {"jpg", "jpeg", "webp", "avif"}:
        if im.mode in ("RGBA", "LA", "P"):  # Has transparency
            # For JPG or when forcing white background: flatten to white
            if fmt in {"jpg", "jpeg"} or force_white_bg:
                bg = Image.new("RGB", im.size, (255, 255, 255))
                if im.mode == "P":
                    im = im.convert("RGBA")
                bg.paste(im.convert("RGBA"), mask=im.convert("RGBA").split()[-1])
                return bg
            # For WebP/AVIF with alpha, RGBA can remain
            if im.mode != "RGBA":
                return im.convert("RGBA")
            return im
        # CMYK/other -> RGB
        if im.mode not in ("RGB", "RGBA"):
            return im.convert("RGB")
        return im
    elif fmt == "png":
        # PNG supports alpha
        if force_white_bg and im.mode in ("RGBA", "LA", "P"):
            # Flatten to white background
            bg = Image.new("RGB", im.size, (255, 255, 255))
            if im.mode == "P":
                im = im.convert("RGBA")
            bg.paste(im.convert("RGBA"), mask=im.convert("RGBA").split()[-1])
            return bg
        # Keep alpha if present
        if im.mode in ("P", "LA"):
            return im.convert("RGBA")
        if im.mode not in ("RGB", "RGBA"):
            return im.convert("RGBA" if "A" in im.getbands() else "RGB")
        return im
    return im

def save_image(im: Image.Image, out_path: Path, out_fmt: str, quality: int, force_white_bg: bool = False):
    out_fmt_upper = out_fmt.upper()
    params = {}
    if out_fmt_upper in {"JPG", "JPEG"}:
        params.update(dict(quality=quality, optimize=True, progressive=True, subsampling="4:2:0"))
        im = pil_mode_for_format(im, "jpg", force_white_bg)
        im.save(out_path, format="JPEG", **params)
    elif out_fmt_upper == "PNG":
        # PNG "quality" not relevant; compress_level 0-9
        im = pil_mode_for_format(im, "png", force_white_bg)
        params.update(dict(compress_level=6))
        im.save(out_path, format="PNG", **params)
    elif out_fmt_upper == "WEBP":
        im = pil_mode_for_format(im, "webp", force_white_bg)
        params.update(dict(quality=quality, method=6))
        im.save(out_path, format="WEBP", **params)
    elif out_fmt_upper == "AVIF":
        if not AVIF_AVAILABLE:
            raise RuntimeError("AVIF wird nicht unterstützt (pillow-avif-plugin nicht installiert).")
        im = pil_mode_for_format(im, "avif", force_white_bg)
        # pillow-avif-plugin uses 'quality'
        params.update(dict(quality=quality))
        im.save(out_path, format="AVIF", **params)
    else:
        raise ValueError(f"Unbekanntes Ausgabeformat: {out_fmt_upper}")

def page_suffix(idx: int) -> str:
    """Generate page suffix for multi-page PDFs: -p001, -p002, ..."""
    return f"-p{idx:03d}"

def unique_target_path(base_dir: Path, base_name: str, ext: str, taken: Dict[str, int], overwrite: bool = False) -> Path:
    """
    Generate unique target path for output file.
    - First occurrence: {base_name}{ext}
    - On collision (if overwrite=False): {base_name}-01{ext}, -02, ...
    - On overwrite (if overwrite=True): existing file will be replaced
    """
    candidate = f"{base_name}{ext}"
    candidate_path = base_dir / candidate

    if overwrite:
        # Overwrite mode: existing files will be replaced
        if candidate not in taken:
            taken[candidate] = 0
        return candidate_path
    else:
        # Increment mode: on collision, create new file with index
        # Check if file exists on disk (not just in memory)
        if candidate_path.exists():
            # File exists, need to find next available number
            num = 1
            while True:
                candidate2 = f"{base_name}-{num:02d}{ext}"
                candidate_path2 = base_dir / candidate2
                if not candidate_path2.exists():
                    taken[candidate2] = 0
                    return candidate_path2
                num += 1
        else:
            # File doesn't exist, use base name
            taken[candidate] = 0
            return candidate_path

def convert_image_file(
    src_path: Path,
    out_dir: Path,
    out_fmt: str,
    target_width: int,
    quality: int,
    taken: Dict[str, int],
    prefix: str = "",
    overwrite: bool = False,
    force_white_bg: bool = False,
):
    im = load_image_fix_orientation(src_path)
    w, h = compute_new_size(im, target_width)
    if (w, h) != im.size:
        im = im.resize((w, h), Image.LANCZOS)

    base_slug = wp_slugify(src_path.stem)
    base_slug = ensure_prefix(base_slug, prefix)
    ext = "." + out_fmt.lower().replace("jpeg", "jpg")
    out_path = unique_target_path(out_dir, base_slug, ext, taken, overwrite)
    save_image(im, out_path, out_fmt, quality, force_white_bg)
    print(f"OK: {src_path.name}  ->  {out_path.name}")

def convert_pdf_file(
    src_path: Path,
    out_dir: Path,
    out_fmt: str,
    target_width: int,
    quality: int,
    taken: Dict[str, int],
    pdf_zoom: float = 2.0,  # ~ 144 DPI (72 * 2)
    prefix: str = "",
    overwrite: bool = False,
    force_white_bg: bool = False,
):
    if not PYMUPDF_AVAILABLE:
        raise RuntimeError(
            "PDF-Konvertierung benötigt PyMuPDF (pymupdf). Bitte mit `pip install pymupdf` installieren."
        )
    doc = fitz.open(src_path)
    base_slug = wp_slugify(src_path.stem)
    base_slug = ensure_prefix(base_slug, prefix)
    ext = "." + out_fmt.lower().replace("jpeg", "jpg")

    for i, page in enumerate(doc, start=1):
        # Render
        mat = fitz.Matrix(pdf_zoom, pdf_zoom)
        pix = page.get_pixmap(matrix=mat, alpha=True)
        mode = "RGBA" if pix.alpha else "RGB"
        im = Image.frombytes(mode, [pix.width, pix.height], pix.samples)

        # Resize
        w, h = compute_new_size(im, target_width)
        if (w, h) != im.size:
            im = im.resize((w, h), Image.LANCZOS)

        # Add page suffix to base slug for multi-page PDFs
        base_with_page = f"{base_slug}{page_suffix(i)}"
        out_path = unique_target_path(out_dir, base_with_page, ext, taken, overwrite)
        save_image(im, out_path, out_fmt, quality, force_white_bg)
        print(f"OK: {src_path.name} [Seite {i}]  ->  {out_path.name}")

    doc.close()


def should_skip_directory(dir_path: Path, exclude_patterns: str) -> bool:
    """
    Check if a directory should be skipped.
    Returns True if any of the exclude_patterns (comma-separated) appears in any part of the directory path.
    """
    if not exclude_patterns:
        return False
    # Parse comma-separated patterns
    patterns = [p.strip() for p in exclude_patterns.split(",") if p.strip()]
    if not patterns:
        return False
    # Check all parts of the path for any exclusion pattern
    for part in dir_path.parts:
        for pattern in patterns:
            if pattern.lower() in part.lower():
                return True
    return False

def should_include_file(file_path: Path, filename_patterns: str) -> bool:
    """
    Check if a file should be included based on filename patterns.
    Returns True if any of the filename_patterns (comma-separated) appears in the filename (without extension).
    """
    if not filename_patterns:
        return True  # No filter = all files
    # Parse comma-separated patterns
    patterns = [p.strip() for p in filename_patterns.split(",") if p.strip()]
    if not patterns:
        return True
    # Check if any pattern matches the filename
    for pattern in patterns:
        if pattern.lower() in file_path.stem.lower():
            return True
    return False

def walk_and_convert(
    in_dir: Path,
    out_dir: Path,
    include_exts: Iterable[str],
    out_fmt: str,
    target_width: int,
    quality: int,
    pdf_zoom: float,
    prefix: str = "",
    exclude_dir_pattern: str = "",
    filename_pattern: str = "",
    overwrite: bool = False,
    force_white_bg: bool = False,
):
    ensure_output_dir(out_dir)

    exts = tuple(e.lower() for e in include_exts)
    taken: Dict[str, int] = {}
    skipped_dirs = set()
    skipped_files = 0

    for src in in_dir.rglob("*"):
        if not src.is_file():
            continue

        # Directory filter: skip files in excluded directories
        if exclude_dir_pattern and should_skip_directory(src.parent, exclude_dir_pattern):
            if src.parent not in skipped_dirs:
                print(f"Überspringe Verzeichnis: {src.parent}")
                skipped_dirs.add(src.parent)
            continue

        ext = src.suffix.lower()
        if ext not in exts:
            continue

        # Filename filter: skip files without the desired pattern
        if filename_pattern and not should_include_file(src, filename_pattern):
            skipped_files += 1
            continue

        try:
            if ext in SUPPORTED_PDF_EXTS:
                convert_pdf_file(
                    src, out_dir, out_fmt, target_width, quality, taken,
                    pdf_zoom=pdf_zoom, prefix=prefix, overwrite=overwrite, force_white_bg=force_white_bg
                )
            elif ext in SUPPORTED_IMAGE_EXTS:
                convert_image_file(
                    src, out_dir, out_fmt, target_width, quality, taken,
                    prefix=prefix, overwrite=overwrite, force_white_bg=force_white_bg
                )
            else:
                print(f"Übersprungen (nicht unterstützt): {src.name}")
        except Exception as e:
            print(f"FEHLER bei {src.name}: {e}")

    if skipped_files > 0:
        print(f"\nÜbersprungene Dateien (Dateinamen-Filter): {skipped_files}")


def main():
    print("=== Batch-Konverter: TIF/JPG/PNG/PDF -> AVIF/WEBP/PNG/JPG (WordPress-optimierte Namen) ===\n")

    in_dir_input = ask("Quellordner eingeben (absoluter Pfad erforderlich)", "")
    if not in_dir_input:
        print("Fehler: Quellordner muss angegeben werden.")
        sys.exit(2)
    in_dir = Path(in_dir_input).expanduser().resolve()
    if not in_dir.exists() or not in_dir.is_dir():
        print(f"Fehler: Quellordner '{in_dir}' existiert nicht.")
        sys.exit(2)

    # Default output directory is a subdirectory of the source folder
    default_out_dir = in_dir / "output-web"
    out_dir_input = ask("Zielordner eingeben", str(default_out_dir))
    out_dir = Path(out_dir_input).expanduser().resolve()

    # Ask for prefix (optional)
    prefix_input = ask("Dateinamen-Prefix (z.B. ABC123, optional - Enter für keinen)", "")
    prefix = normalize_prefix(prefix_input)
    if prefix_input and prefix:
        print(f"  → Normalisierter Prefix: '{prefix}'")
    elif prefix_input and not prefix:
        print("  → Warnung: Prefix enthält keine gültigen Zeichen und wird ignoriert.")

    # Ask for overwrite mode
    overwrite_choice = ask("Existierende Dateien im Zielordner überschreiben? (y/n)", "n").lower()
    overwrite = overwrite_choice == "y"
    if overwrite:
        print("  → Existierende Dateien werden überschrieben")
    else:
        print("  → Bei Namenskollisionen werden neue Dateien mit Index erstellt (-01, -02, ...)")

    # Ask for white background option (default: yes)
    white_bg_choice = ask("Transparenz durch weißen Hintergrund ersetzen? (y/n)", "y").lower()
    force_white_bg = white_bg_choice == "y"
    if force_white_bg:
        print("  → Transparenz wird durch weißen Hintergrund ersetzt")
    else:
        print("  → Transparenz bleibt erhalten (wo unterstützt)")

    # Ask for filter options
    use_filters = ask("Datei-Filter aktivieren? (y/n)", "n").lower()
    exclude_dir_pattern = ""
    filename_pattern = ""

    if use_filters == "y":
        exclude_dir_pattern = ask("Verzeichnisse ausschließen mit Muster (kommagetrennt, z.B. 'backup,excl,temp', Enter für keinen)", "")
        if exclude_dir_pattern:
            patterns = [p.strip() for p in exclude_dir_pattern.split(",") if p.strip()]
            print(f"  → Verzeichnisse mit diesen Mustern werden übersprungen: {', '.join(patterns)}")

        filename_pattern = ask("Nur Dateien verarbeiten mit Muster im Namen (kommagetrennt, z.B. '_web,final', Enter für alle)", "")
        if filename_pattern:
            patterns = [p.strip() for p in filename_pattern.split(",") if p.strip()]
            print(f"  → Nur Dateien mit diesen Mustern werden verarbeitet: {', '.join(patterns)}")

    include = ask("Dateimuster (Komma-getrennt), z.B. tif,jpg,png,pdf", "tif,jpg,jpeg,png,pdf")
    include_exts = parse_ext_list(include)

    out_fmt = ask("Zielformat (avif/webp/png/jpg)", "webp").lower()
    if out_fmt not in {"avif", "webp", "png", "jpg", "jpeg"}:
        print("Fehler: Ungültiges Zielformat.")
        sys.exit(3)
    if out_fmt == "jpeg":
        out_fmt = "jpg"
    if out_fmt == "avif" and not AVIF_AVAILABLE:
        print("Hinweis: AVIF-Support nicht gefunden. Installiere `pillow-avif-plugin`, oder wähle ein anderes Format.")
        proceed = ask("Trotzdem fortfahren (y/n)?", "n").lower()
        if proceed != "y":
            sys.exit(4)

    target_width_str = ask("Ziel-Bildbreite in Pixel (Höhe proportional)", "1920")
    try:
        target_width = max(1, int(target_width_str))
    except ValueError:
        print("Fehler: Zielbreite muss eine Ganzzahl sein.")
        sys.exit(5)

    quality_default = "80" if out_fmt in {"webp", "jpg", "avif"} else "0"
    quality_str = ask("Qualität (0-100, höher = besser; PNG ignoriert es)", quality_default)
    try:
        quality = min(100, max(0, int(quality_str)))
    except ValueError:
        print("Fehler: Qualität muss 0-100 sein.")
        sys.exit(6)

    pdf_zoom_str = ask("PDF-Render-Zoom (1.0 ≈ 72 DPI, 2.0 ≈ 144 DPI)", "2.0")
    try:
        pdf_zoom = max(0.1, float(pdf_zoom_str))
    except ValueError:
        print("Fehler: PDF-Zoom muss Zahl sein.")
        sys.exit(7)

    print("\nStarte Verarbeitung …\n")
    walk_and_convert(
        in_dir=in_dir,
        out_dir=out_dir,
        include_exts=include_exts,
        out_fmt=out_fmt,
        target_width=target_width,
        quality=quality,
        pdf_zoom=pdf_zoom,
        prefix=prefix,
        exclude_dir_pattern=exclude_dir_pattern,
        filename_pattern=filename_pattern,
        overwrite=overwrite,
        force_white_bg=force_white_bg,
    )
    print("\nFertig.")


if __name__ == "__main__":
    main()
