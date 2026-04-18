from datetime import datetime
import json
import os
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
import csv


from utils.txt_file_proc import process_documents
# from utils.img_files_proc import process_img_files
from utils.struct_files_proc import process_struct_files
from utils.web_files_proc import process_web_files


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


STRUCT_EXT = {'csv', 'json', 'parquet'}
DOC_EXT = {'pdf', 'rtf', 'tif', 'tiff'}
WEB_EXT = {'html', 'htm'}
IMAGE_EXT = {'jpg', 'jpeg', 'png', 'gif', 'bmp'}

target_dir = "./ПДнDataset"
output_path = "scan_results.csv"


# Расширения файлов (примеры, подставьте свои)
STRUCT_EXT = {'.csv', '.json', '.parquet'}
DOC_EXT = {'.pdf', '.rtf', '.tif', '.tiff'}
WEB_EXT = {'.html', '.htm'}
IMAGE_EXT = {'.jpg', '.jpeg', '.png', '.gif', '.bmp'}

def scan(target_dir, batch_size=50, output_csv="scan_results.csv"):
    # Буферы для пакетной отправки
    buffers = {
        'struct': [],
        'doc': [],
        'web': [],    
        # 'image': [], 
    }
    
    # Сопоставление категорий с обработчиками
    handlers = {
        'struct': process_struct_files,
        'doc': process_documents,
        'web': process_web_files,  
        # 'image': process_img_files
    }
    
    total_files = 0
    all_results = []   # <-- здесь будут собираться все результаты

    with ProcessPoolExecutor(max_workers=1) as executor:
        futures = []
        
        def flush_buffer(category):
            if buffers[category]:
                batch = buffers[category].copy()
                buffers[category].clear()
                futures.append(executor.submit(handlers[category], batch))
                logger.debug(f"Отправлен пакет {category}: {len(batch)} файлов")
        
        # Обход директории
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                full_path = os.path.join(root, file)
                ext = os.path.splitext(file)[1].lower()
                
                # Структурированные данные
                if ext in STRUCT_EXT:
                    buffers['struct'].append(full_path)
                    total_files += 1
                    if len(buffers['struct']) >= batch_size:
                        flush_buffer('struct')
                
                # Документы (PDF, RTF, TIFF)
                elif ext in DOC_EXT:
                    buffers['doc'].append(full_path)
                    total_files += 1
                    if len(buffers['doc']) >= batch_size:
                        flush_buffer('doc')
                
                # Веб и изображения пока пропускаем (можно раскомментировать при необходимости)
                elif ext in WEB_EXT:
                    buffers['web'].append(full_path)
                    total_files += 1
                    if len(buffers['web']) >= batch_size:
                        flush_buffer('web')

                # elif ext in IMAGE_EXT:
                #     buffers['image'].append(full_path)
                #     total_files += 1
                #     if len(buffers['image']) >= batch_size:
                #         flush_buffer('image')

        # Отправляем остатки из буферов
        for category in buffers.keys():
            if category in handlers:   # только те, для которых есть обработчик
                flush_buffer(category)
        
        logger.info(f"Всего файлов к обработке: {total_files}")
        processed = 0
        
        # Сбор результатов
        for future in as_completed(futures):
            try:
                batch_results = future.result()
                for result in batch_results:
                    processed += 1
                    all_results.append(result)   
                    
                    if result.get('pii_found'):
                        logger.warning(f"Найдены ПДн в {result['file']}: {result['pii']}")
                    else:
                        logger.info(f"Файл {result['file']} обработан, ПДн не найдены")
            except Exception as e:
                logger.error(f"Ошибка в обработчике: {e}", exc_info=True)
        
        logger.info(f"Обработано файлов: {processed} из {total_files}")
        
        # Генерация отчётов
        if all_results:
            generate_final_report(all_results)
            export_to_csv(all_results, output_csv)
        else:
            logger.warning("Нет результатов для создания отчёта")


def generate_final_report(results):
    report_path = f"scan_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    summary = {
        'total_files': len(results),
        'by_protection_level': {1: 0, 2: 0, 3: 0, 4: 0},
        'files_with_pii': 0,
        'max_level': 4,
        'details': []
    }
    for res in results:
        level = res.get('protection_level', 4)
        summary['by_protection_level'][level] += 1
        if res.get('pii_found'):
            summary['files_with_pii'] += 1
        summary['details'].append({
            'file': res['file'],
            'level': level,
            'pii_found': res['pii_found'],
            'categories': list(res.get('pii', {}).keys()) if res['pii_found'] else []
        })
    if summary['files_with_pii'] > 0:
        summary['max_level'] = max(level for level, count in summary['by_protection_level'].items() if count > 0)
    else:
        summary['max_level'] = 4

    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    logger.info(f"Итоговый отчёт сохранён в {report_path}")
    # Краткая сводка в консоль
    print("\n=== СВОДКА ПО УРОВНЯМ ЗАЩИЩЁННОСТИ ===")
    for level in [1,2,3,4]:
        print(f"УЗ-{level}: {summary['by_protection_level'][level]} файлов")
    print(f"Максимальный требуемый УЗ: {summary['max_level']}")

def export_to_csv(results, output_path):
    rows = []
    for res in results:
        file_path = res['file']
        pii = res.get('pii', {})
        # Собираем список категорий, в которых были находки
        categories = [cat for cat, items in pii.items() if items]
        # Суммарное количество найденных объектов ПДн
        total_finds = sum(len(items) for items in pii.values())
        # Уровень защищённости 
        level = res.get('protection_level', 'не определён')
        # Расширение файла
        ext = os.path.splitext(file_path)[1].lower() or 'без расширения'
        rows.append({
            'path': file_path,
            'categories': ', '.join(categories) if categories else 'нет',
            'uz': total_finds,
            'total_hits': level,
            'ext': ext
        })


    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['path', 'categories', 'uz', 'total_hits', 'ext'])
        writer.writeheader()
        writer.writerows(rows)

    logger.info(f"CSV-отчёт сохранён в {output_path}")


if __name__ == '__main__':
    target_dir = "./ПДнDataset"
    scan(target_dir=target_dir)