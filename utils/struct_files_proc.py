import os
import logging
import json
import csv
from typing import List, Dict, Any
import pandas as pd

from functions import detect_pii


logger = logging.getLogger(__name__)

def process_csv(file_path: str) -> str:
    rows = []
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.reader(f)
        for row in reader:
            rows.append(' '.join(str(cell) for cell in row))
    return ' '.join(rows)

def process_json(file_path: str) -> str:
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        data = json.load(f)
    
    def extract_strings(obj):
        if isinstance(obj, str):
            return obj
        elif isinstance(obj, dict):
            return ' '.join(extract_strings(v) for v in obj.values())
        elif isinstance(obj, list):
            return ' '.join(extract_strings(item) for item in obj)
        else:
            return str(obj)
    
    return extract_strings(data)

def process_parquet(file_path: str) -> str:
    df = pd.read_parquet(file_path)
    # Преобразуем все значения в строки и объединяем
    return ' '.join(df.astype(str).values.flatten())

def process_struct_files(file_paths: List[str]) -> List[Dict[str, Any]]:
    results = []
    for file_path in file_paths:
        try:
            ext = os.path.splitext(file_path)[1].lower()
            if ext == '.csv':
                text = process_csv(file_path)
            elif ext == '.json':
                text = process_json(file_path)
            elif ext == '.parquet':
                text = process_parquet(file_path)
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