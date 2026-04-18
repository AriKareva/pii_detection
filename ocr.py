import json
import os
import easyocr
import cv2
import numpy as np
from PIL import Image


_reader = easyocr.Reader(['ru', 'en'], gpu=False)

# utils/text_extractors.py (фрагменты)

def ocr_from_image(img_array: np.ndarray) -> str:
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 11, 2)
    processed = cv2.cvtColor(binary, cv2.COLOR_GRAY2RGB)
    result = _reader.readtext(processed, detail=0)
    # result — это список строк, объединяем их через пробел
    return ' '.join(result)

# def extract_from_tiff(file_path: str) -> str:
#     img = Image.open(file_path)
#     pages_text = []
#     for i in range(img.n_frames):
#         img.seek(i)
#         frame = np.array(img.convert('RGB'))
#         text = _ocr_from_image(frame)
#         pages_text.append(text)
#     return '\n'.join(pages_text)

# def extract_from_pdf(file_path: str) -> str:
    # doc = fitz.open(file_path)
    # full_text = []
    # for page_num in range(len(doc)):
    #     page = doc.load_page(page_num)
    #     text = page.get_text()
    #     if text.strip():
    #         full_text.append(text)
    #     else:
    #         pix = page.get_pixmap(dpi=200)
    #         img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    #         if pix.n == 4:
    #             img = img[:, :, :3]
    #         ocr_text = _ocr_from_image(img)
    #         full_text.append(ocr_text)
    # doc.close()
    # return '\n'.join(full_text)