# Batch Asset Converter for WordPress

A Python tool for batch converting images and PDFs into web-optimized formats with WordPress-friendly filenames. Available as both a command-line interface and a user-friendly web GUI.

## Features

- **Multi-format Support**: Convert TIF, JPG, PNG, BMP, GIF, and PDF files
- **Modern Output Formats**: AVIF, WebP, PNG, or JPG
- **WordPress-Optimized Naming**: Automatic SEO-friendly slug generation
- **Filename Prefix Support**: Optional prefix for organized file naming (e.g., `abc123-`)
- **Smart Output Directory**: Defaults to `output-web` subfolder in source directory
- **Flexible File Overwrite**: Choose to overwrite existing files or create new ones with incremental naming
- **Advanced Filtering**: Exclude directories by pattern and filter files by name
- **Smart Image Processing**: Auto-resize, EXIF orientation correction, color mode handling
- **Large Image Support**: Handles high-resolution images up to 300 megapixels
- **PDF to Image**: Convert multi-page PDFs to individual images
- **Collision-Safe**: Automatic handling of duplicate filenames
- **Quality Control**: Configurable compression and quality settings
- **Dual Interface**: Choose between CLI or Web GUI

## Installation

### Basic Installation (CLI Only)

Install core dependencies for command-line usage:

```bash
pip install -r requirements.txt
```

### Full Installation (CLI + Web GUI)

Install all dependencies including the web interface:

```bash
pip install -r requirements.txt -r requirements-gui.txt
```

### Manual Installation

Core dependencies:
```bash
pip install Pillow pymupdf pillow-avif-plugin
```

For web GUI, additionally install:
```bash
pip install gradio
```

## Usage

### Web Interface (Recommended for Most Users)

Launch the web GUI for an intuitive, visual experience:

```bash
python web_gui.py
```

This will:
- Start a local web server (default: `http://localhost:7860`)
- Automatically open the interface in your default browser
- Provide real-time conversion progress updates
- Include folder browser dialogs for easy path selection

**Features:**
- Visual folder selection with browse buttons
- Real-time conversion status display
- Light/dark mode toggle
- All CLI features accessible through the GUI
- Responsive design with monochrome theme

<!-- Screenshot placeholders - Add your screenshots here -->
#### Screenshots

**Light Mode:**
![Web GUI Light Mode](docs/screenshots/web-gui-light.png)
*Web interface in light mode showing conversion settings and real-time status*

**Dark Mode:**
![Web GUI Dark Mode](docs/screenshots/web-gui-dark.png)
*Web interface in dark mode with inverted logo and theme colors*

**Conversion in Progress:**
![Conversion Progress](docs/screenshots/web-gui-progress.png)
*Real-time conversion status with detailed file processing information*

> **Note:** To add screenshots later, create a `docs/screenshots/` directory and add your images with these filenames.

### Command Line Interface

For automation, scripting, or terminal workflows:

```bash
python batch_convert_assets.py
```

You'll be prompted for:

1. **Source Directory**: Path to input files (default: current directory)
2. **Output Directory**: Path for converted files (default: `<source-dir>/output-web`)
3. **Filename Prefix**: Optional prefix for all output files (e.g., `ABC123`)
4. **Overwrite Mode**: Choose to overwrite existing files or create new ones with index
5. **File Filtering**: Optionally enable advanced filtering
   - **Directory Exclusion**: Skip directories containing a pattern (e.g., `excl`)
   - **Filename Pattern**: Only process files containing a pattern (e.g., `_web`)
6. **File Extensions**: Comma-separated list (default: `tif,jpg,jpeg,png,pdf`)
7. **Target Format**: Output format - `avif`, `webp`, `png`, or `jpg` (default: `webp`)
8. **Target Width**: Maximum width in pixels (default: `1920`)
9. **Quality**: Compression quality 0-100 (default: `80`)
10. **PDF Zoom**: Rendering resolution for PDFs (default: `2.0` ≈ 144 DPI)

#### Example CLI Session

```
=== Batch-Konverter: TIF/JPG/PNG/PDF -> AVIF/WEBP/PNG/JPG (WordPress-optimierte Namen) ===

Quellordner eingeben [.]: /path/to/images
Zielordner eingeben [/path/to/images/output-web]:
Dateinamen-Prefix (z.B. ABC123, optional - Enter für keinen) []: PRJ001
  → Normalisierter Prefix: 'prj001-'
Existierende Dateien im Zielordner überschreiben? (y/n) [n]: n
  → Bei Namenskollisionen werden neue Dateien mit Index erstellt (-001, -002, ...)
Datei-Filter aktivieren? (y/n) [n]: y
Verzeichnisse ausschließen mit Muster [...] []: backup
  → Verzeichnisse mit 'backup' werden übersprungen
Nur Dateien verarbeiten mit Muster im Namen [...] []: _web
  → Nur Dateien mit '_web' im Namen werden verarbeitet
Dateimuster (Komma-getrennt), z.B. tif,jpg,png,pdf [tif,jpg,jpeg,png,pdf]: png,jpg
Zielformat (avif/webp/png/jpg) [webp]: webp
Ziel-Bildbreite in Pixel (Höhe proportional) [1920]: 1920
Qualität (0-100, höher = besser; PNG ignoriert es) [80]: 85
PDF-Render-Zoom (1.0 ≈ 72 DPI, 2.0 ≈ 144 DPI) [2.0]: 2.0

Starte Verarbeitung …
```

## How It Works

### WordPress-Friendly Naming

The script automatically converts filenames to WordPress-compatible slugs:

| Original Filename | Without Prefix | With Prefix `abc123` |
|------------------|----------------|----------------------|
| `Mein Bild Ü.jpg` | `mein-bild-ue.webp` | `abc123-mein-bild-ue.webp` |
| `Café_Photo.png` | `cafe-photo.webp` | `abc123-cafe-photo.webp` |
| `Straße 123.tif` | `strasse-123.webp` | `abc123-strasse-123.webp` |

**Transformations:**
- German umlauts: ä→ae, ö→oe, ü→ue, ß→ss
- Removes diacritics and special characters
- Converts to lowercase
- Replaces spaces and special chars with hyphens
- Optionally adds prefix at the beginning (normalized to lowercase, alphanumeric only)
- Handles duplicate names with `-001`, `-002` suffixes

**Prefix Feature:**
- Enter a prefix like `ABC123` or `Project-42` when prompted
- Normalized to: `abc123-` or `project42-`
- Smart detection: won't duplicate if filename already has the prefix
- Press Enter to skip prefix (optional)

### File Overwrite Control

Choose how to handle existing files in the output directory:

**Overwrite Mode (y):**
- Existing files are replaced with newly converted versions
- Useful for refreshing an entire output directory
- Example: `photo.webp` exists → overwrites `photo.webp`

**Keep Mode (n - default):**
- Creates new files with incremental suffixes on name collision
- Preserves existing files in the output directory
- Example: `photo.webp` exists → creates `photo-001.webp`
- Further collisions create `photo-002.webp`, `photo-003.webp`, etc.

### Advanced Filtering

Optional filtering system to control which files are processed:

**Directory Exclusion:**
- Skip directories containing a specific pattern in their path
- Case-insensitive matching
- Example: Pattern `backup` skips `/photos/backup/`, `/backup-2024/`, etc.
- Press Enter to skip directory filtering (processes all directories)

**Filename Pattern:**
- Only process files containing a specific pattern in their name
- Case-insensitive matching
- Example: Pattern `_web` only processes `photo_web.jpg`, `image_web_final.png`
- Press Enter to skip filename filtering (processes all matching files)

### Image Processing

- **Auto-resize**: Images wider than target width are scaled down proportionally
- **EXIF correction**: Automatically fixes image orientation based on EXIF data
- **Color mode handling**: Converts CMYK to RGB, handles transparency appropriately
- **Format-specific optimization**:
  - **JPG**: Progressive encoding, 4:2:0 chroma subsampling, optimize flag
  - **PNG**: Compression level 6
  - **WebP**: Method 6 for better compression
  - **AVIF**: Quality-based encoding

### PDF Conversion

- Each PDF page becomes a separate image file
- Naming convention: `filename-p001.webp`, `filename-p002.webp`, etc.
- Configurable rendering resolution (zoom factor)
- Supports both RGB and RGBA rendering

## Output Structure

All converted files are placed in the output directory with flat structure (no subdirectories), making them easy to bulk upload to WordPress media library.

## Technical Details

### Project Structure

```
batch_convert_wp/
├── batch_convert_assets.py    # Core conversion engine (CLI)
├── web_gui.py                  # Web interface (Gradio)
├── requirements.txt            # Core dependencies
├── requirements-gui.txt        # GUI dependencies
├── README.md                   # This file
└── .gitignore                  # Git ignore rules
```

### Supported Input Formats
- Images: `.jpg`, `.jpeg`, `.png`, `.tif`, `.tiff`, `.bmp`, `.gif`
- Documents: `.pdf` (requires PyMuPDF)

### Supported Output Formats
- **AVIF**: Modern, highly compressed (requires pillow-avif-plugin)
- **WebP**: Modern, good browser support
- **PNG**: Lossless, best for graphics with transparency
- **JPG**: Lossy, universal compatibility

### Performance Tips
- Larger zoom values for PDFs result in better quality but larger files
- Quality 80-85 offers good balance for WebP/AVIF
- Use WebP for broad compatibility, AVIF for maximum compression
- Web GUI shows real-time progress in both the interface and console

## Error Handling

The tool will:
- Skip unsupported file types
- Continue processing if individual files fail
- Display error messages for failed conversions
- Warn if optional dependencies are missing
- Show detailed error traces in the web GUI

## Troubleshooting

### "Pillow ist nicht installiert"
Install Pillow: `pip install Pillow`

### "AVIF wird nicht unterstützt"
Install AVIF plugin: `pip install pillow-avif-plugin`

### "PDF-Konvertierung benötigt PyMuPDF"
Install PyMuPDF: `pip install pymupdf`

### Web GUI won't start
Make sure Gradio is installed: `pip install gradio`

### Images appear rotated
The script automatically handles EXIF orientation. If images still appear rotated, the source file may have incorrect metadata.

### Low quality output
Increase the quality parameter (recommended: 85-95 for important images)

### DecompressionBombWarning for large images
The script handles images up to 300 megapixels. If you need to process even larger images, this limit can be adjusted in the code.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**TL;DR:** You can use, modify, and distribute this software freely, even for commercial purposes. Just keep the copyright notice and attribution.

## Contributing

Feel free to modify and extend this tool for your needs. Common enhancements:
- Add command-line argument support
- Implement parallel processing for faster conversion
- Add watermarking capabilities
- Support additional metadata preservation
- Extend the web GUI with additional features

## Credits

Developed with focus on WordPress media library optimization and user-friendly batch processing.
