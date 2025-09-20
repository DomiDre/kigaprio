from pathlib import Path

from paddleocr import PaddleOCR

script_dir = Path(__file__).parent.resolve()
project_dir = script_dir.parent
image_dir = project_dir / "images"

ocr = PaddleOCR(
    use_doc_orientation_classify=True,
    use_doc_unwarping=True,
    use_textline_orientation=True,
)

# Run OCR inference on a sample image
result = ocr.predict(input=str(image_dir / "20250917_070143.jpg"))

# Visualize the results and save the JSON results
for res in result:
    res.print()
    res.save_to_img("output")
    res.save_to_json("output")
