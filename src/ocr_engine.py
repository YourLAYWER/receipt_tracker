import os
import sys
import cv2
from paddleocr import PaddleOCR

# Initialize PaddleOCR once (downloads lightweight models on first run)
ocr = PaddleOCR(
    use_doc_orientation_classify=True,
    use_doc_unwarping=True,
    use_textline_orientation=False,
)


def resize_for_cpu(image_path: str, max_dim: int = 1600):
  """Loads an image with OpenCV and downscales it if it's too large for fast CPU OCR."""
  img = cv2.imread(image_path)
  if img is None:
    raise FileNotFoundError(f"Could not read image at: {image_path}")

  height, width = img.shape[:2]
  if max(height, width) > max_dim:
    scale = max_dim / max(height, width)
    img = cv2.resize(
        img, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA
    )
  return img


def extract_receipt_text(image_path: str, save_debug: bool = True) -> list[dict]:
  """Runs OCR on a receipt image and returns structured text lines."""
  img = resize_for_cpu(image_path)
  results = ocr.predict(img)

  extracted_lines = []
  for res in results:
    if save_debug:
      res.save_to_img("output")

    for text, score, box in zip(
        res["rec_texts"], res["rec_scores"], res["rec_polys"]
    ):
      extracted_lines.append({
          "text": text.strip(),
          "confidence": round(float(score), 3),
          "box": box.tolist(),
      })

  return extracted_lines


if __name__ == "__main__":
  if len(sys.argv) < 2:
    print("Usage: python src/ocr_engine.py data/sample_receipts/receipt1.jpg")
    sys.exit(1)

  img_path = sys.argv[1]
  lines = extract_receipt_text(img_path)

  print(f"\n--- Extracted {len(lines)} lines from {os.path.basename(img_path)} ---\n")
  for item in lines:
    print(f"[{item['confidence']:.2f}] {item['text']}")