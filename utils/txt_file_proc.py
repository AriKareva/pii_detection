import os
import logging
import numpy as np
from PIL import Image
import fitz
from striprtf.striprtf import rtf_to_text
import easyocr
import cv2

from functions import detect_pii   # или from pii_detectors import detect_all_personal_data

logger = logging.getLogger(__name__)


_reader = None

def _get_reader():
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(['ru', 'en'], gpu=False)
    return _reader

def _ocr_from_image(img_array: np.ndarray) -> str:
    # Предобработка: адаптивная бинаризация
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    processed = cv2.cvtColor(binary, cv2.COLOR_GRAY2RGB)

    reader = _get_reader()
    result = reader.readtext(processed, detail=0)
    return ' '.join(result)

def ocr_image(source):
    if isinstance(source, str):
        img = Image.open(source).convert('RGB')
        img_array = np.array(img)
    elif isinstance(source, np.ndarray):
        img_array = source
    else:
        raise TypeError("source must be a file path or numpy array")

    return _ocr_from_image(img_array)



def extract_pdf_text(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    full_text = []
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text()
        if text.strip():
            full_text.append(text)
        else:
            # Рендерим страницу как изображение и применяем OCR
            pix = page.get_pixmap(dpi=200)
            img_data = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, pix.n
            )
            if pix.n == 4:   # RGBA -> RGB
                img_data = img_data[:, :, :3]
            ocr_text = ocr_image(img_data)
            full_text.append(ocr_text)
    doc.close()
    return '\n'.join(full_text)


def extract_rtf_text(rtf_path: str) -> str:
    with open(rtf_path, 'r', encoding='utf-8', errors='ignore') as f:
        rtf_content = f.read()
    return rtf_to_text(rtf_content)


def extract_tiff_text(tiff_path: str) -> str:
    img = Image.open(tiff_path)
    pages_text = []

    # Проверяем, является ли изображение многостраничным
    try:
        # Пытаемся получить количество кадров
        n_frames = getattr(img, 'n_frames', 1)
    except Exception:
        n_frames = 1   # если не получилось, считаем одностраничным

    # Обрабатываем все страницы
    for i in range(n_frames):
        try:
            img.seek(i)
        except EOFError:
            # Достигнут конец файла (если n_frames был определён неправильно)
            break
        frame = np.array(img.convert('RGB'))
        text = ocr_image(frame)   # ваша функция OCR
        pages_text.append(text)

    return '\n'.join(pages_text)


def process_documents(file_paths):
    results = []
    for file_path in file_paths:
        try:
            ext = os.path.splitext(file_path)[1].lower()

            if ext in ('.tif', '.tiff'):
                text = extract_tiff_text(file_path)
            elif ext == '.pdf':
                text = extract_pdf_text(file_path)
            elif ext == '.rtf':
                text = extract_rtf_text(file_path)
            else:
                logger.warning(f"Неподдерживаемое расширение: {file_path}")
                continue

            pii = detect_pii(text)
            results.append({
                'file': file_path,
                'pii_found': len(pii) > 0,
                'pii': pii
            })
        except Exception as e:
            logger.error(f"Ошибка обработки {file_path}: {e}")
            results.append({
                'file': file_path,
                'pii_found': False,
                'error': str(e)
            })
    return results