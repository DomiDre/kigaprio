from dataclasses import dataclass
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np


@dataclass
class TableCell:
    """Represents a single cell in the table"""

    row: int
    col: int
    x: int
    y: int
    width: int
    height: int
    image: np.ndarray


class TableExtractor:
    def __init__(self, debug=False):
        """
        Initialize the table extractor

        Args:
            debug: If True, shows intermediate processing steps
        """
        self.debug = debug

    def preprocess_image(self, image: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """
        Preprocess the image for better line detection

        Args:
            image: Input image (BGR or grayscale)

        Returns:
            Tuple of (grayscale image, binary image)
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)

        # Use Otsu's thresholding for better binarization
        _, binary = cv2.threshold(
            blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )

        if self.debug:
            cv2.imshow("Binary Image", cv2.resize(binary, None, fx=0.5, fy=0.5))
            cv2.waitKey(0)

        return gray, binary

    def detect_grid_lines(self, binary: np.ndarray) -> tuple[list[int], list[int]]:
        """
        Detect horizontal and vertical lines using projection profiles

        Args:
            binary: Binary image (white lines on black background)

        Returns:
            Tuple of (horizontal_positions, vertical_positions)
        """
        height, width = binary.shape

        # Detect horizontal lines using horizontal projection
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (width // 4, 1))
        horizontal_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)

        # Find horizontal line positions
        horizontal_projection = np.sum(horizontal_lines, axis=1)
        h_threshold = np.max(horizontal_projection) * 0.3
        h_lines = []
        in_line = False
        line_start = 0

        for i, val in enumerate(horizontal_projection):
            if val > h_threshold and not in_line:
                in_line = True
                line_start = i
            elif val <= h_threshold and in_line:
                in_line = False
                h_lines.append((line_start + i) // 2)  # Use middle of the line

        # Detect vertical lines using vertical projection
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, height // 4))
        vertical_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel)

        # Find vertical line positions
        vertical_projection = np.sum(vertical_lines, axis=0)
        v_threshold = np.max(vertical_projection) * 0.3
        v_lines = []
        in_line = False
        line_start = 0

        for i, val in enumerate(vertical_projection):
            if val > v_threshold and not in_line:
                in_line = True
                line_start = i
            elif val <= v_threshold and in_line:
                in_line = False
                v_lines.append((line_start + i) // 2)  # Use middle of the line

        if self.debug:
            # Visualize detected lines
            debug_img = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
            for y in h_lines:
                cv2.line(debug_img, (0, y), (width, y), (0, 255, 0), 2)
            for x in v_lines:
                cv2.line(debug_img, (x, 0), (x, height), (0, 0, 255), 2)
            cv2.imshow("Detected Lines", cv2.resize(debug_img, None, fx=0.5, fy=0.5))
            cv2.waitKey(0)

        return h_lines, v_lines

    def refine_grid_lines(
        self,
        h_lines: list[int],
        v_lines: list[int],
        image_shape: tuple,
        expected_cols: int = 7,
    ) -> tuple[list[int], list[int]]:
        """
        Refine detected lines and ensure we have the expected number of columns

        Args:
            h_lines: Detected horizontal line positions
            v_lines: Detected vertical line positions
            image_shape: Shape of the image (height, width)
            expected_cols: Expected number of columns

        Returns:
            Refined (horizontal_positions, vertical_positions)
        """
        height, width = image_shape[:2]

        # Sort lines
        h_lines = sorted(h_lines)
        v_lines = sorted(v_lines)

        # Merge lines that are too close (within 20 pixels)
        h_lines = self.merge_close_lines(h_lines, min_distance=20)
        v_lines = self.merge_close_lines(v_lines, min_distance=20)

        # Add borders if missing
        if not h_lines or h_lines[0] > height * 0.1:
            h_lines.insert(0, 0)
        if not h_lines or h_lines[-1] < height * 0.9:
            h_lines.append(height - 1)

        if not v_lines or v_lines[0] > width * 0.1:
            v_lines.insert(0, 0)
        if not v_lines or v_lines[-1] < width * 0.9:
            v_lines.append(width - 1)

        # Check if we have the right number of columns
        detected_cols = len(v_lines) - 1

        if detected_cols != expected_cols:
            print(f"Detected {detected_cols} columns, expected {expected_cols}")

            # Try to find the table region and create uniform grid
            if len(v_lines) >= 2:
                # Use the leftmost and rightmost detected lines
                left = v_lines[0]
                right = v_lines[-1]
            else:
                # Use image boundaries with some margin
                left = int(width * 0.05)
                right = int(width * 0.95)

            # Create uniform vertical grid
            step = (right - left) / expected_cols
            v_lines = [int(left + i * step) for i in range(expected_cols + 1)]
            print(f"Created uniform grid with {expected_cols} columns")

        return h_lines, v_lines

    def merge_close_lines(self, lines: list[int], min_distance: int = 20) -> list[int]:
        """
        Merge lines that are too close together

        Args:
            lines: List of line positions
            min_distance: Minimum distance between lines

        Returns:
            Merged lines
        """
        if not lines:
            return lines

        merged = [lines[0]]
        for line in lines[1:]:
            if line - merged[-1] >= min_distance:
                merged.append(line)

        return merged

    def extract_cells(
        self, image: np.ndarray, h_lines: list[int], v_lines: list[int]
    ) -> list[list[TableCell]]:
        """
        Extract individual cells from the image using grid lines

        Args:
            image: Original image
            h_lines: Horizontal line positions
            v_lines: Vertical line positions

        Returns:
            2D list of TableCell objects
        """
        cells = []

        for i in range(len(h_lines) - 1):
            row_cells = []
            for j in range(len(v_lines) - 1):
                # Get cell boundaries with small margin
                margin = 3
                y1 = h_lines[i] + margin
                y2 = h_lines[i + 1] - margin
                x1 = v_lines[j] + margin
                x2 = v_lines[j + 1] - margin

                # Ensure valid boundaries
                y1 = max(0, y1)
                y2 = min(image.shape[0], y2)
                x1 = max(0, x1)
                x2 = min(image.shape[1], x2)

                if y2 > y1 and x2 > x1:
                    cell_img = image[y1:y2, x1:x2]

                    cell = TableCell(
                        row=i,
                        col=j,
                        x=v_lines[j],
                        y=h_lines[i],
                        width=v_lines[j + 1] - v_lines[j],
                        height=h_lines[i + 1] - h_lines[i],
                        image=cell_img,
                    )
                    row_cells.append(cell)

            if row_cells:
                cells.append(row_cells)

        return cells

    def process_image(
        self, image_path: str, expected_cols: int = 7
    ) -> list[list[TableCell]]:
        """
        Main processing pipeline - simplified version without contour detection

        Args:
            image_path: Path to the input image
            expected_cols: Expected number of columns (default 7)

        Returns:
            2D list of extracted cells
        """
        # Read image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not read image from {image_path}")

        print(f"Image shape: {image.shape}")

        # Preprocess
        gray, binary = self.preprocess_image(image)

        # Detect grid lines
        h_lines, v_lines = self.detect_grid_lines(binary)
        print(
            f"Initial detection: {len(h_lines)} horizontal lines, {len(v_lines)} vertical lines"
        )

        # Refine grid to match expected columns
        h_lines, v_lines = self.refine_grid_lines(
            h_lines, v_lines, image.shape, expected_cols
        )
        print(f"After refinement: {len(h_lines) - 1} rows, {len(v_lines) - 1} columns")

        # Extract cells using the original image
        cells = self.extract_cells(image, h_lines, v_lines)

        return cells

    def visualize_grid(
        self,
        image_path: str,
        cells: list[list[TableCell]],
        save_path: str | None = None,
    ):
        """
        Visualize the detected grid overlaid on the original image

        Args:
            image_path: Path to original image
            cells: Extracted cells
            save_path: Optional path to save visualization
        """
        image = cv2.imread(image_path)
        if image is None:
            return

        # Draw grid lines
        overlay = image.copy()

        # Draw all cell boundaries
        for row in cells:
            for cell in row:
                # Draw cell rectangle
                cv2.rectangle(
                    overlay,
                    (cell.x, cell.y),
                    (cell.x + cell.width, cell.y + cell.height),
                    (0, 255, 0),
                    2,
                )

                # Add cell label
                label = f"R{cell.row + 1}C{cell.col + 1}"
                cv2.putText(
                    overlay,
                    label,
                    (cell.x + 5, cell.y + 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    (255, 0, 0),
                    1,
                )

        # Show or save
        if save_path:
            cv2.imwrite(save_path, overlay)
            print(f"Grid visualization saved to {save_path}")
        else:
            cv2.imshow("Grid Overlay", cv2.resize(overlay, None, fx=0.5, fy=0.5))
            cv2.waitKey(0)
            cv2.destroyAllWindows()

    def visualize_cells(
        self, cells: list[list[TableCell]], save_path: str | None = None
    ):
        """
        Visualize extracted cells in a grid layout

        Args:
            cells: 2D list of cells
            save_path: Optional path to save the visualization
        """
        if not cells:
            print("No cells to visualize")
            return

        rows = len(cells)
        cols = len(cells[0]) if rows > 0 else 0

        if rows == 0 or cols == 0:
            print("Empty cell grid")
            return

        # Create figure with appropriate size
        fig, axes = plt.subplots(rows, cols, figsize=(cols * 2, rows * 1.5))

        # Handle single row or column
        if rows == 1 and cols == 1:
            axes = [[axes]]
        elif rows == 1:
            axes = [axes]
        elif cols == 1:
            axes = [[ax] for ax in axes]

        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        # for i, row in enumerate(cells):
        #     for j, cell in enumerate(row):
        #         ax = axes[i][j] if rows > 1 else axes[j]

        # # Display the cell image
        # if len(cell.image.shape) == 2:
        #     ax.imshow(cell.image, cmap="gray")
        # else:
        #     ax.imshow(cv2.cvtColor(cell.image, cv2.COLOR_BGR2RGB))

        # # Set title with day name if available
        # title = f"Week {i + 1}\n{days[j] if j < len(days) else f'Col {j + 1}'}"
        # ax.set_title(title, fontsize=8)
        # ax.axis("off")

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            print(f"Cell visualization saved to {save_path}")
        else:
            plt.show()


# Example usage
def main():
    # Initialize the extractor
    extractor = TableExtractor(debug=False)

    # Process an image
    script_dir = Path(__file__).parent.resolve()
    project_dir = script_dir.parent
    image_dir = project_dir / "images"
    image_path = str(image_dir / "20250917_070143.jpg")

    try:
        # Extract cells - specify we expect exactly 7 columns
        cells = extractor.process_image(image_path, expected_cols=7)

        print(
            f"Extracted {len(cells)} rows with {len(cells[0]) if cells else 0} columns"
        )

        # Visualize results
        extractor.visualize_cells(cells, save_path="extracted_grid.png")

        # Save individual cells for OCR processing
        days = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]

        for i, row in enumerate(cells):
            for j, cell in enumerate(row):
                if j < len(days):  # Ensure we don't exceed day names
                    # Save each cell as an image
                    cell_path = f"week_{i + 1}_{days[j]}.png"
                    cv2.imwrite(cell_path, cell.image)
                    print(f"Saved cell for Week {i + 1}, {days[j]}")

                    # Here you can send cell.image to your OCR module
                    # ocr_result = process_cell_with_ocr(cell)
                    # print(f"Week {i+1}, {days[j]}: Priority {ocr_result}")

    except Exception as e:
        print(f"Error processing image: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
