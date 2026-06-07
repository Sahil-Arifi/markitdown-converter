# MarkItDown Converter

A modern drag-and-drop desktop app that converts any file to clean Markdown using Microsoft's [markitdown](https://github.com/microsoft/markitdown) library.

## Supported Formats

PDF, DOCX, PPTX, XLSX, HTML, and more.

## Installation

```bash
pip install markitdown[all] PyQt6
```

## Run

```bash
python3 app.py
```

Or double-click `MarkItDown.command` (macOS).

## Why

Sending raw files to LLMs wastes tokens on formatting overhead. Converting to Markdown first strips all that noise — same content, far fewer tokens.
