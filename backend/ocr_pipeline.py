import os
from pdf2image import convert_from_path
import pytesseract
from paddleocr import PaddleOCR
from typing import List

# Convert PDF to images
def pdf_to_images(pdf_path: str, output_folder: str = "temp_images") -> List[str]:
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    images = convert_from_path(pdf_path)
    image_paths = []
    for i, img in enumerate(images):
        img_path = os.path.join(output_folder, f"page_{i+1}.png")
        img.save(img_path, "PNG")
        image_paths.append(img_path)
    return image_paths

# OCR using pytesseract
def ocr_image_pytesseract(image_path: str) -> str:
    return pytesseract.image_to_string(image_path)

# OCR using PaddleOCR
def ocr_image_paddle(image_path: str, ocr=None) -> str:
    if ocr is None:
        ocr = PaddleOCR(use_angle_cls=True, lang='en')
    result = ocr.ocr(image_path, cls=True)
    text = "\n".join([line[1][0] for line in result[0]])
    return text

# OCR all images in a folder
def ocr_images(image_paths: List[str], method: str = "pytesseract") -> List[str]:
    texts = []
    if method == "paddle":
        ocr = PaddleOCR(use_angle_cls=True, lang='en')
        for img_path in image_paths:
            texts.append(ocr_image_paddle(img_path, ocr))
    else:
        for img_path in image_paths:
            texts.append(ocr_image_pytesseract(img_path))
    return texts 