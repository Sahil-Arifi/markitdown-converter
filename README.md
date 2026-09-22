# MarkItDown Converter

A Python desktop interface for converting supported documents to Markdown with Microsoft's [MarkItDown](https://github.com/microsoft/markitdown). Built with PyQt6.

## Features

- Add multiple local files by dragging them into the window or using the file picker.
- Choose an output directory.
- Convert queued files in a background thread.
- Track progress and see success or error messages for each file.
- Write one UTF-8 Markdown file per input.

## Install and run

Use a Python environment compatible with the installed MarkItDown and PyQt6 releases:

```bash
python -m pip install "markitdown[all]" PyQt6
python app.py
```

The repository contains the Python application; it does not include a packaged executable or macOS launcher script.

## Usage

1. Add files with **Choose Files** or drag and drop.
2. Select **Change Output** if needed. The default directory is `~/Desktop/md conversion`.
3. Select **Convert**.
4. Review each file's result and open the output directory.

The generated filename uses the input's stem, such as `report.pdf` becoming `report.md`.

## Supported inputs and limits

Format support comes from the installed MarkItDown converters and their dependencies. The interface targets formats such as PDF, DOCX, PPTX, XLSX, and HTML; it cannot convert every possible file or guarantee that layout and content will be preserved.

- Inputs with the same filename stem write to the same output path and can overwrite earlier output.
- **Open Output Folder** currently uses the macOS `open` command. On other systems, open the directory manually.
- Dependencies are not pinned and no automated tests are included.
- The app does not measure token savings or guarantee a reduction for a particular document or model.

## Implementation

[app.py](app.py) contains the PyQt6 interface, a conversion worker using Python threads, Qt signals for progress updates, and the MarkItDown conversion calls.
