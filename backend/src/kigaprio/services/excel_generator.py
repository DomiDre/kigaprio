"""Excel generation service."""

from typing import List, Dict, Any
import pandas as pd


class ExcelGenerator:
    """Service for generating Excel reports."""

    def generate_report(self, results: List[Dict[str, Any]], output_path: str) -> str:
        """Generate Excel report from analysis results."""

        # Prepare data for DataFrame
        rows = []

        for result in results:
            row = {
                "Filename": result["filename"],
                "File Type": result["file_type"],
                "File Size (bytes)": result["file_size"],
            }

            # Add analysis data
            analysis = result.get("analysis", {})
            if "error" in analysis:
                row["Status"] = "Error"
                row["Error"] = analysis["error"]
            else:
                row["Status"] = "Success"

                # Add type-specific data
                if result["file_type"] in [
                    ".jpg",
                    ".jpeg",
                    ".png",
                    ".gif",
                    ".bmp",
                    ".tiff",
                ]:
                    row.update(
                        {
                            "Width": analysis.get("width"),
                            "Height": analysis.get("height"),
                            "Format": analysis.get("format"),
                            "Mode": analysis.get("mode"),
                            "Has Transparency": analysis.get("has_transparency"),
                            "Color Count": analysis.get("color_count"),
                        }
                    )
                elif result["file_type"] == ".pdf":
                    row.update(
                        {
                            "Page Count": analysis.get("page_count"),
                            "Character Count": analysis.get("character_count"),
                            "Text Preview": analysis.get("text_preview", "")[:100]
                            + "..."
                            if analysis.get("text_preview")
                            else "",
                        }
                    )

            rows.append(row)

        # Create DataFrame and save to Excel
        df = pd.DataFrame(rows)

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Analysis Results", index=False)

            # Auto-adjust columns width
            worksheet = writer.sheets["Analysis Results"]
            for column in worksheet.columns:
                max_length = 0
                column = [cell for cell in column]
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[
                    column[0].column_letter
                ].width = adjusted_width

        return output_path
