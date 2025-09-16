"""File processing service."""

from pathlib import Path
from typing import Any

import pypdf
from PIL import Image


class FileProcessor:
    """Service for processing uploaded files."""

    async def process_file(self, file_path: str) -> dict[str, Any]:
        """Process a single file and extract information."""

        path = Path(file_path)
        file_ext = path.suffix.lower()

        result = {
            "filename": path.name,
            "file_type": file_ext,
            "file_size": path.stat().st_size,
            "analysis": {},
        }

        if file_ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"]:
            result["analysis"] = await self._process_image(file_path)
        elif file_ext == ".pdf":
            result["analysis"] = await self._process_pdf(file_path)
        else:
            result["analysis"] = {"error": "Unsupported file type"}

        return result

    async def _process_image(self, file_path: str) -> dict[str, Any]:
        """Process image file."""

        try:
            with Image.open(file_path) as img:
                return {
                    "width": img.width,
                    "height": img.height,
                    "format": img.format,
                    "mode": img.mode,
                    "has_transparency": img.mode in ("RGBA", "LA")
                    or "transparency" in img.info,
                    "color_count": len(img.getcolors() or [])
                    if img.mode in ("P", "L")
                    else "N/A",
                }
        except Exception as e:
            return {"error": f"Failed to process image: {str(e)}"}

    async def _process_pdf(self, file_path: str) -> dict[str, Any]:
        """Process PDF file."""

        try:
            with open(file_path, "rb") as file:
                pdf_reader = pypdf.PdfReader(file)

                page_count = len(pdf_reader.pages)
                text_content = ""

                # Extract text from first few pages
                for page in pdf_reader.pages[:3]:  # First 3 pages
                    text_content += page.extract_text()

                return {
                    "page_count": page_count,
                    "text_preview": text_content[:500] + "..."
                    if len(text_content) > 500
                    else text_content,
                    "character_count": len(text_content),
                    "metadata": pdf_reader.metadata,
                }
        except Exception as e:
            return {"error": f"Failed to process PDF: {str(e)}"}
