import os
import sys
from pathlib import Path
from bs4 import BeautifulSoup
import logging
from functions import detect_pii

logger = logging.getLogger(__name__)


def extract_text_from_html(html_file_path: str, output_file: str = None) -> str:
    html_path = Path(html_file_path)
    if not html_path.is_file():
        raise FileNotFoundError(f"Файл не найден: {html_file_path}")

    # Чтение файла с указанием кодировки (можно заменить на автоматическое определение)
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Парсинг HTML
    soup = BeautifulSoup(html_content, 'html.parser')

    # Удаляем элементы, которые обычно не несут смыслового текста
    for tag in soup(['script', 'style', 'meta', 'link', 'noscript', 'head']):
        tag.decompose()

    # Извлечение текста с разделением пробелами
    text = soup.get_text(separator=' ', strip=True)

    # Дополнительная очистка от лишних пробелов и пустых строк
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    clean_text = '\n'.join(chunk for chunk in chunks if chunk)

    # Сохранение в файл, если указано
    if output_file:
        output_path = Path(output_file)
        output_path.write_text(clean_text, encoding='utf-8')
        print(f"Текст сохранён в: {output_path.resolve()}")

    return clean_text


def process_web_files(file_paths):
    results = []
    for file_path in file_paths:
        try:
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext == '.html':
                text = extract_text_from_html(file_path)
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