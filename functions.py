import os
import re
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import warnings


warnings.filterwarnings("ignore", message=".*Using CPU.*")

CATEGORY_TO_GROUP = {
    'passport': 'УЗ-3',
    'snils': 'УЗ-3',
    'driver_license': 'УЗ-3',
    'inn': 'УЗ-3',
    'full_name': 'УЗ-4',
    'birth_info': 'УЗ-4',
    'address': 'УЗ-4',
    'phone': 'УЗ-4',
    'email': 'УЗ-4',
    'bank_details': 'УЗ-2',
    'biometric': 'УЗ-1',
    'health': 'УЗ-1',
    'beliefs': 'УЗ-1',
    'ethnicity': 'УЗ-1',
}

def clean_document(text: str, remove_linebreaks: bool = True, normalize_spaces: bool = True) -> str:
    if remove_linebreaks:
        text = re.sub(r'[\n\r\t]+', ' ', text)
    if normalize_spaces:
        text = re.sub(r'\s+', ' ', text)
    return text.strip()

def _luhn_check(card_number: str) -> bool:
    """Алгоритм Луна для проверки номера банковской карты."""
    digits = re.sub(r'\D', '', card_number)
    if not digits or len(digits) < 13 or len(digits) > 19:
        return False
    total = 0
    reverse_digits = digits[::-1]
    for i, d in enumerate(reverse_digits):
        n = int(d)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


VALID_REGION_CODES = {
    '01', '03', '04', '05', '07', '08', '10', '11', '12', '14',
    '15', '17', '18', '19', '20', '22', '24', '25', '26', '27',
    '28', '29', '30', '32', '33', '34', '35', '36', '37', '38',
    '39', '40', '41', '42', '44', '45', '46', '47', '49', '50',
    '51', '52', '53', '54', '56', '57', '58', '60', '61', '63',
    '64', '65', '66', '68', '69', '70', '71', '73', '74', '75',
    '76', '77', '78', '79', '80', '81', '82', '83', '86', '87',
    '89', '91', '92', '94', '95'
}

def detect_passport_numbers(text: str, context_window: int = 50, require_context: bool = True) -> List[Dict]:
    context_keywords = ['паспорт', 'passport', 'серия', 'номер', 'удостоверение',
                        'документ', 'паспорта', 'passp', 'удост', 'личность']
    patterns = [
        re.compile(r'\b(\d{2})[-\s](\d{2})[-\s](\d{3})[-\s]?(\d{3})\b'),
        re.compile(r'\b(\d{2})(\d{2})(\d{6})\b'),
    ]
    matches = []
    for pattern in patterns:
        for match in pattern.finditer(text):
            groups = match.groups()
            if len(groups) == 4:
                region_code, year_code, serial_number = groups[0], groups[1], groups[2] + groups[3]
            elif len(groups) == 3:
                region_code, year_code, serial_number = groups[0], groups[1], groups[2]
            else:
                continue
            full_match = match.group(0)
            start, end = match.start(), match.end()
            if region_code not in VALID_REGION_CODES:
                continue
            current_year_2digit = datetime.now().year % 100
            year_int = int(year_code)
            if not (97 <= year_int <= 99 or 0 <= year_int <= current_year_2digit + 5):
                continue
            if serial_number == '000000':
                continue
            if require_context:
                left = text[max(0, start - context_window):start].lower()
                right = text[end:end + context_window].lower()
                if not any(kw in left + ' ' + right for kw in context_keywords):
                    continue
            matches.append({
                'value': full_match,
                'start': start,
                'end': end,
                'category': 'passport',
                'group': CATEGORY_TO_GROUP['passport']
            })
    # Удаление дубликатов
    unique = []
    seen = set()
    for m in matches:
        pos = (m['start'], m['end'])
        if pos not in seen:
            seen.add(pos)
            unique.append(m)
    return unique


def _check_snils_control_sum(digits: str) -> bool:
    if len(digits) != 11 or digits == '00000000000':
        return False
    try:
        nums = [int(d) for d in digits]
    except ValueError:
        return False
    total = sum(nums[i] * (9 - i) for i in range(9))
    remainder = total % 101
    expected = 0 if remainder == 100 else remainder
    return expected == nums[9] * 10 + nums[10]

def detect_snils_numbers(text: str, context_window: int = 50, require_context: bool = True) -> List[Dict]:
    context_keywords = ['снилс', 'страховое', 'пенсионное', 'свидетельство',
                        'ссопс', 'индивидуального', 'лицевого', 'счёта', 'счета', 'счет',
                        'snils', 'пенс', 'страх']
    pattern = re.compile(r'\b(\d{3})[-\s.]?(\d{3})[-\s.]?(\d{3})[-\s.]?(\d{2})\b')
    matches = []
    for match in pattern.finditer(text):
        groups = match.groups()
        full_digits = groups[0] + groups[1] + groups[2] + groups[3]
        start, end = match.start(), match.end()
        matched_text = match.group(0)
        if not _check_snils_control_sum(full_digits):
            continue
        if require_context:
            left = text[max(0, start - context_window):start].lower()
            right = text[end:end + context_window].lower()
            if not any(kw in left + ' ' + right for kw in context_keywords):
                continue
        matches.append({
            'value': matched_text,
            'start': start,
            'end': end,
            'category': 'snils',
            'group': CATEGORY_TO_GROUP['snils']
        })
    unique = []
    seen = set()
    for m in matches:
        pos = (m['start'], m['end'])
        if pos not in seen:
            seen.add(pos)
            unique.append(m)
    return unique


VALID_REGION_CODES_FOR_DRIVER_LICENSE = {
    '01','02','03','04','05','06','07','08','09','10','11','12','13','14','15','16','17','18','19','20',
    '21','22','23','24','25','26','27','28','29','30','31','32','33','34','35','36','37','38','39','40',
    '41','42','43','44','45','46','47','48','49','50','51','52','53','54','55','56','57','58','59','60',
    '61','62','63','64','65','66','67','68','69','70','71','72','73','74','75','76','77','78','79',
    '82','92','80','81','84','85',
    '102','116','118','122','125','138','150','152','159','161','163','164','173','174','177','178','186','190','196','197','198','199',
    '716','750','752','754','756','758','760','761','763','764','765','766','767','768','769','770','771','772','773','774','775','776',
    '777','778','779','780','781','782','783','784','785','786','787','788','789','790','791','792','793','794','795','796','797','798','799'
}

def detect_driver_license_numbers(text: str, context_window: int = 50, require_context: bool = True) -> List[Dict]:
    context_keywords = ['водительское удостоверение', 'водительского удостоверения',
                        'в/у', 'ву', 'права', 'прав', 'driver license', "driver's license",
                        'driving licence', 'driving license', 'водительские права',
                        'вод. удостоверение', 'удостоверение водителя', 'разреш. кат.',
                        'гибдд', 'гаи', 'категория', 'кат.', 'в/у']
    matches = []
    # Современный формат
    modern = re.compile(r'\b(\d{4})(\d{6})\b')
    for m in modern.finditer(text):
        series, number = m.group(1), m.group(2)
        full = m.group(0)
        start, end = m.start(), m.end()
        region = series[:2]
        if region not in VALID_REGION_CODES_FOR_DRIVER_LICENSE:
            continue
        if require_context:
            left = text[max(0, start - context_window):start].lower()
            right = text[end:end + context_window].lower()
            if not any(kw in left + ' ' + right for kw in context_keywords):
                continue
        matches.append({
            'value': full,
            'start': start,
            'end': end,
            'category': 'driver_license',
            'group': CATEGORY_TO_GROUP['driver_license']
        })
    # Старый формат
    old = re.compile(r'(?:^|\s)(\d{2})([А-ЯA-Z]{2})(\d{6})(?=\s|$|[.,;:!?])', re.IGNORECASE)
    for m in old.finditer(text):
        region, letters, number = m.group(1), m.group(2).upper(), m.group(3)
        full = m.group(0).strip()
        start, end = m.start(1), m.end(3)
        if region not in VALID_REGION_CODES_FOR_DRIVER_LICENSE:
            continue
        if require_context:
            left = text[max(0, start - context_window):start].lower()
            right = text[end:end + context_window].lower()
            if not any(kw in left + ' ' + right for kw in context_keywords):
                continue
        matches.append({
            'value': full,
            'start': start,
            'end': end,
            'category': 'driver_license',
            'group': CATEGORY_TO_GROUP['driver_license']
        })
    unique = []
    seen = set()
    for m in matches:
        pos = (m['start'], m['end'])
        if pos not in seen:
            seen.add(pos)
            unique.append(m)
    return unique


def _validate_inn_10(digits: str) -> bool:
    if len(digits) != 10 or not digits.isdigit():
        return False
    coeffs = [2, 4, 10, 3, 5, 9, 4, 6, 8]
    total = sum(int(digits[i]) * coeffs[i] for i in range(9))
    control = total % 11
    if control > 9:
        control = 0
    return control == int(digits[9])

def _validate_inn_12(digits: str) -> bool:
    if len(digits) != 12 or not digits.isdigit():
        return False
    coeffs1 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
    total1 = sum(int(digits[i]) * coeffs1[i] for i in range(10))
    control1 = total1 % 11
    if control1 > 9:
        control1 = 0
    if control1 != int(digits[10]):
        return False
    coeffs2 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
    total2 = sum(int(digits[i]) * coeffs2[i] for i in range(11))
    control2 = total2 % 11
    if control2 > 9:
        control2 = 0
    return control2 == int(digits[11])

def detect_inn_numbers(text: str, context_window: int = 50, require_context: bool = True) -> List[Dict]:
    context_keywords = ['инн', 'налогоплательщик', 'налогоплательщика', 'свидетельство',
                        'индивидуальный номер', 'идентификационный номер',
                        'налоговая', 'фнс', 'огрн', 'огрнип', 'inn', 'tax id']
    pattern = re.compile(r'\b(\d{4})[-\s]?(\d{6})(?:[-\s]?(\d{2}))?\b')
    matches = []
    for match in pattern.finditer(text):
        groups = match.groups()
        if groups[2] is not None:
            full_digits = groups[0] + groups[1] + groups[2]
            is_valid = _validate_inn_12(full_digits)
        else:
            full_digits = groups[0] + groups[1]
            is_valid = _validate_inn_10(full_digits)
        if not is_valid or full_digits == '0' * len(full_digits):
            continue
        start, end = match.start(), match.end()
        matched_text = match.group(0)
        if require_context:
            left = text[max(0, start - context_window):start].lower()
            right = text[end:end + context_window].lower()
            if not any(kw in left + ' ' + right for kw in context_keywords):
                continue
        matches.append({
            'value': matched_text,
            'start': start,
            'end': end,
            'category': 'inn',
            'group': CATEGORY_TO_GROUP['inn']
        })
    unique = []
    seen = set()
    for m in matches:
        pos = (m['start'], m['end'])
        if pos not in seen:
            seen.add(pos)
            unique.append(m)
    return unique


SURNAME_SUFFIXES = (r'ов(?:а|ой)?$', r'ев(?:а|ой)?$', r'ёв(?:а|ой)?$',
                    r'ин(?:а|ой)?$', r'ын(?:а|ой)?$', r'ский$', r'ская$',
                    r'цкий$', r'цкая$', r'ой$', r'ая$', r'ий$', r'ый$', r'их$', r'ых$',
                    r'енко$', r'ко$', r'ук$', r'юк$', r'ак$', r'вич$', r'вна$')
PATRONYMIC_SUFFIXES = (r'ович$', r'евич$', r'ич$', r'овна$', r'евна$', r'ична$', r'на$')

def _is_surname(word: str) -> bool:
    if len(word) < 4: return False
    for s in SURNAME_SUFFIXES:
        if re.search(s, word, re.IGNORECASE): return True
    return False

def _is_patronymic(word: str) -> bool:
    if len(word) < 5: return False
    for s in PATRONYMIC_SUFFIXES:
        if re.search(s, word, re.IGNORECASE): return True
    return False

def _is_capitalized(word: str) -> bool:
    return bool(re.match(r'^[А-ЯЁ][а-яё]+$', word))

def _extract_words_with_positions(text: str) -> List[Tuple[str, int, int]]:
    words = []
    for m in re.finditer(r'\b[А-ЯЁа-яё]+(?:-[А-ЯЁа-яё]+)?\b', text):
        words.append((m.group(), m.start(), m.end()))
    return words

def detect_full_names(text: str, context_window: int = 40, require_context: bool = True) -> List[Dict]:
    context_keywords = ['фио', 'фамилия', 'имя', 'отчество', 'подпись', 'представитель',
                        'сотрудник', 'работник', 'заявитель', 'владелец', 'ф.и.о.',
                        'ф. и. о.', 'подписал', 'утверждаю', 'согласовано',
                        'исполнитель', 'директор', 'начальник', 'специалист', 'менеджер',
                        'гражданин', 'гражданка', 'рождения', 'паспорт', 'выдан']
    words = _extract_words_with_positions(text)
    if len(words) < 2:
        return []
    matches = []
    used = set()
    for i, (word, w_start, w_end) in enumerate(words):
        is_sn = _is_surname(word)
        is_pat = _is_patronymic(word)
        if not (is_sn or is_pat):
            continue
        # Случай 1: имя перед
        if i > 0:
            prev_word, prev_start, prev_end = words[i-1]
            if _is_capitalized(prev_word) and not _is_surname(prev_word) and not _is_patronymic(prev_word) and len(prev_word) >= 3:
                if i > 1:
                    prev_prev_word, pps, ppe = words[i-2]
                    if _is_capitalized(prev_prev_word):
                        if _is_surname(prev_prev_word) and is_pat:
                            full_text = f"{prev_prev_word} {prev_word} {word}"
                            matches.append({'value': full_text, 'start': pps, 'end': w_end})
                            used.update([i-2, i-1, i])
                            continue
                        elif _is_patronymic(prev_prev_word) and is_sn:
                            full_text = f"{prev_prev_word} {prev_word} {word}"
                            matches.append({'value': full_text, 'start': pps, 'end': w_end})
                            used.update([i-2, i-1, i])
                            continue
                pair = f"{prev_word} {word}"
                matches.append({'value': pair, 'start': prev_start, 'end': w_end})
                used.update([i-1, i])
                continue
        # Случай 2: фамилия перед именем
        if i < len(words) - 1 and is_sn:
            next_word, next_start, next_end = words[i+1]
            if _is_capitalized(next_word) and not _is_surname(next_word) and not _is_patronymic(next_word) and len(next_word) >= 3:
                if i < len(words) - 2:
                    next_next_word, nns, nne = words[i+2]
                    if _is_capitalized(next_next_word) and _is_patronymic(next_next_word):
                        full_text = f"{word} {next_word} {next_next_word}"
                        matches.append({'value': full_text, 'start': w_start, 'end': nne})
                        used.update([i, i+1, i+2])
                        continue
                pair = f"{word} {next_word}"
                matches.append({'value': pair, 'start': w_start, 'end': next_end})
                used.update([i, i+1])
                continue
    # Фильтрация контекстом и пересечениями
    matches.sort(key=lambda x: (x['start'], -(x['end'] - x['start'])))
    filtered = []
    last_end = -1
    for m in matches:
        if m['start'] >= last_end:
            if require_context:
                left = text[max(0, m['start'] - context_window):m['start']].lower()
                right = text[m['end']:m['end'] + context_window].lower()
                if not any(kw in left + ' ' + right for kw in context_keywords):
                    continue
            m['category'] = 'full_name'
            m['group'] = CATEGORY_TO_GROUP['full_name']
            filtered.append(m)
            last_end = m['end']
    return filtered


def detect_phones(text: str) -> List[Dict]:
    pattern = re.compile(r'(?:\+7|8)\s*\(?\d{3}\)?[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}\b')
    matches = []
    for m in pattern.finditer(text):
        matches.append({
            'value': m.group(),
            'start': m.start(),
            'end': m.end(),
            'category': 'phone',
            'group': CATEGORY_TO_GROUP['phone']
        })
    return matches

def detect_emails(text: str) -> List[Dict]:
    pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    matches = []
    for m in pattern.finditer(text):
        matches.append({
            'value': m.group(),
            'start': m.start(),
            'end': m.end(),
            'category': 'email',
            'group': CATEGORY_TO_GROUP['email']
        })
    return matches

def detect_bank_details(text: str) -> List[Dict]:
    patterns = [
        (re.compile(r'\b\d{9}\b'), 'БИК', False),
        (re.compile(r'\b\d{20}\b'), 'расчётный счёт', False),
        (re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'), 'карта', True),
    ]
    matches = []
    for pat, ptype, need_luhn in patterns:
        for m in pat.finditer(text):
            value = m.group(0)
            if need_luhn and not _luhn_check(value):
                continue
            matches.append({
                'value': value,
                'start': m.start(),
                'end': m.end(),
                'type': ptype,
                'category': 'bank_details',
                'group': CATEGORY_TO_GROUP['bank_details']
            })
    return matches


def detect_birth_info(text: str, context_window: int = 50, require_context: bool = True) -> List[Dict]:
    context_keywords = ['рождения', 'родился', 'родилась', 'место рождения',
                        'дата рождения', 'день рождения', 'birth date', 'birth place',
                        'рожд.', 'г.р.', 'д.р.']
    matches = []
    date_patterns = [
        re.compile(r'\b(0[1-9]|[12]\d|3[01])[./](0[1-9]|1[0-2])[./](19|20)\d{2}\b'),
        re.compile(r'\b(19|20)\d{2}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])\b'),
        re.compile(r'\b(0?[1-9]|[12]\d|3[01])\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+(19|20)\d{2}\s*(?:года|г\.?)?\b', re.IGNORECASE)
    ]
    for pat in date_patterns:
        for m in pat.finditer(text):
            start, end = m.start(), m.end()
            date_str = m.group(0)
            if require_context:
                left = text[max(0, start - context_window):start].lower()
                right = text[end:end + context_window].lower()
                if not any(kw in left + ' ' + right for kw in context_keywords):
                    continue
            matches.append({
                'value': date_str,
                'start': start,
                'end': end,
                'category': 'birth_info',
                'group': CATEGORY_TO_GROUP['birth_info']
            })
    # Убираем дубликаты
    unique = []
    seen = set()
    for m in matches:
        pos = (m['start'], m['end'])
        if pos not in seen:
            seen.add(pos)
            unique.append(m)
    return unique


def detect_addresses(text: str, context_window: int = 50, require_context: bool = True) -> List[Dict]:
    context_keywords = ['адрес', 'проживает', 'проживающий', 'зарегистрирован', 'прописка',
                        'место жительства', 'место пребывания', 'адрес регистрации',
                        'фактический адрес', 'почтовый адрес', 'address', 'location']
    matches = []
    full_pattern = re.compile(
        r'\b(\d{6})\s*,\s*(?:г\.|гор\.|город)?\s*[А-ЯЁ][а-яё\s\-\.]+,\s*'
        r'(?:ул\.|улица|пр-т|проспект|пер\.|переулок|б-р|бульвар|пл\.|площадь)\s*'
        r'[А-ЯЁ][а-яё\s\-\.]+,\s*д\.\s*\d+[А-Яа-я]?(?:/\d+)?'
        r'(?:\s*,\s*(?:кв\.|квартира|оф\.|офис)\s*\d+)?\b',
        re.IGNORECASE
    )
    for m in full_pattern.finditer(text):
        addr = m.group(0)
        start, end = m.start(), m.end()
        if require_context:
            left = text[max(0, start - context_window):start].lower()
            right = text[end:end + context_window].lower()
            if not any(kw in left + ' ' + right for kw in context_keywords):
                continue
        matches.append({'value': addr, 'start': start, 'end': end})
    simple_pattern = re.compile(
        r'\b(?:г\.|гор\.|город)?\s*[А-ЯЁ][а-яё\s\-\.]+,\s*'
        r'(?:ул\.|улица|пр-т|проспект)\s*[А-ЯЁ][а-яё\s\-\.]+,\s*д\.\s*\d+[А-Яа-я]?\b',
        re.IGNORECASE
    )
    for m in simple_pattern.finditer(text):
        addr = m.group(0)
        start, end = m.start(), m.end()
        if any(s['start'] <= start <= s['end'] or s['start'] <= end <= s['end'] for s in matches):
            continue
        if require_context:
            left = text[max(0, start - context_window):start].lower()
            right = text[end:end + context_window].lower()
            if not any(kw in left + ' ' + right for kw in context_keywords):
                continue
        matches.append({'value': addr, 'start': start, 'end': end})
    for m in matches:
        m['category'] = 'address'
        m['group'] = CATEGORY_TO_GROUP['address']
    unique = []
    seen = set()
    for m in matches:
        pos = (m['start'], m['end'])
        if pos not in seen:
            seen.add(pos)
            unique.append(m)
    return unique


def _keyword_detector(text: str, keywords: List[str], category: str) -> List[Dict]:
    pattern = re.compile(r'\b(?:' + '|'.join(keywords) + r')\b', re.IGNORECASE)
    matches = []
    for m in pattern.finditer(text):
        start, end = m.start(), m.end()
        ctx_start = max(0, start - 20)
        ctx_end = min(len(text), end + 20)
        matches.append({
            'value': text[ctx_start:ctx_end].strip(),
            'start': ctx_start,
            'end': ctx_end,
            'category': category,
            'group': CATEGORY_TO_GROUP[category]
        })
    unique = []
    seen = set()
    for m in matches:
        pos = (m['start'], m['end'])
        if pos not in seen:
            seen.add(pos)
            unique.append(m)
    return unique

def detect_biometric_data(text: str, context_window=50, require_context=True) -> List[Dict]:
    keywords = ['отпечаток пальца', 'отпечатки пальцев', 'дактилоскопия', 'fingerprint',
                'радужная оболочка', 'радужка', 'сетчатка глаза', 'iris', 'retina',
                'голос', 'тембр голоса', 'voice', 'voiceprint',
                'днк', 'dna', 'генетический', 'геном',
                'распознавание лица', 'изображение лица', 'face recognition',
                'рост', 'вес', 'height', 'weight',
                'биометрия', 'биометрический', 'biometric',
                'рисунок вен', 'геометрия руки', 'ладонь', 'palm', 'vein']
    return _keyword_detector(text, keywords, 'biometric')

def detect_health_data(text: str, context_window=50, require_context=True) -> List[Dict]:
    keywords = ['диагноз', 'diagnosis', 'заболевание', 'болезнь', 'disease', 'illness',
                'инвалид', 'инвалидность', 'disability',
                'медицинская карта', 'история болезни', 'medical record',
                'анализ крови', 'анализ мочи', 'blood test', 'urine test',
                'группа крови', 'blood type', 'аллергия', 'allergy',
                'хронический', 'chronic', 'онкология', 'cancer', 'опухоль', 'tumor',
                'диабет', 'diabetes', 'гипертония', 'hypertension', 'астма', 'asthma',
                'эпилепсия', 'epilepsy', 'психическое расстройство', 'mental disorder',
                'беременность', 'pregnancy', 'больничный лист', 'лист нетрудоспособности', 'sick leave',
                'состояние здоровья', 'health condition', 'health status']
    return _keyword_detector(text, keywords, 'health')

def detect_beliefs(text: str, context_window=50, require_context=True) -> List[Dict]:
    keywords = ['религия', 'religion', 'православие', 'orthodox', 'католицизм', 'catholic',
                'протестантизм', 'protestant', 'ислам', 'мусульманин', 'islam', 'muslim',
                'иудаизм', 'иудей', 'judaism', 'jewish', 'буддизм', 'буддист', 'buddhism', 'buddhist',
                'атеист', 'атеизм', 'atheist', 'atheism', 'вероисповедание', 'конфессия', 'confession',
                'религиозные убеждения', 'religious beliefs', 'церковь', 'church', 'мечеть', 'mosque',
                'синагога', 'synagogue', 'политические взгляды', 'political views',
                'политическая партия', 'political party', 'либерал', 'liberal', 'консерватор', 'conservative',
                'демократ', 'democrat', 'республиканец', 'republican', 'социалист', 'socialist',
                'коммунист', 'communist', 'националист', 'nationalist', 'оппозиция', 'opposition',
                'политические убеждения', 'political beliefs', 'идеология', 'ideology',
                'философские убеждения', 'philosophical beliefs']
    return _keyword_detector(text, keywords, 'beliefs')

def detect_ethnicity(text: str, context_window=50, require_context=True) -> List[Dict]:
    keywords = ['национальность', 'nationality', 'национальная принадлежность', 'ethnicity',
                'раса', 'race', 'расовая принадлежность',
                'русский', 'русская', 'russian', 'татарин', 'татарка', 'tatar',
                'украинец', 'украинка', 'ukrainian', 'белорус', 'белоруска', 'belarusian',
                'армянин', 'армянка', 'armenian', 'азербайджанец', 'азербайджанка', 'azerbaijani',
                'казах', 'казашка', 'kazakh', 'еврей', 'еврейка', 'jewish', 'немец', 'немка', 'german',
                'поляк', 'полька', 'polish', 'чеченец', 'чеченка', 'chechen',
                'дагестанец', 'дагестанка', 'dagestani', 'башкир', 'башкирка', 'bashkir',
                'чуваш', 'чувашка', 'chuvash', 'мордвин', 'мордовка', 'mordvin',
                'удмурт', 'удмуртка', 'udmurt', 'мариец', 'марийка', 'mari',
                'осетин', 'осетинка', 'ossetian', 'бурят', 'бурятка', 'buryat', 'якут', 'якутка', 'yakut',
                'кавказец', 'кавказка', 'азиат', 'азиатка', 'asian',
                'европеоид', 'европеоидная', 'caucasian', 'негроид', 'негроидная', 'negroid',
                'монголоид', 'монголоидная', 'mongoloid']
    return _keyword_detector(text, keywords, 'ethnicity')

# def detect_special_categories(text: str, context_window=50, require_context=True) -> List[Dict]:
#     keywords = ['интимная жизнь', 'intimate life', 'сексуальная ориентация', 'sexual orientation',
#                 'сексуальные предпочтения', 'sexual preferences', 'гетеросексуал', 'гомосексуал', 'бисексуал',
#                 'heterosexual', 'homosexual', 'bisexual', 'судимость', 'criminal record', 'судим', 'судима',
#                 'convicted', 'условный срок', 'probation', 'погашенная судимость', 'expunged',
#                 'привлекался', 'привлекалась', 'arrested', 'член партии', 'party member',
#                 'профсоюз', 'trade union', 'labor union']
#     return _keyword_detector(text, keywords, 'special_categories')


def detect_pii(text: str) -> Dict[str, List[Dict]]:
    detectors = {
        'passport': detect_passport_numbers,
        'snils': detect_snils_numbers,
        'driver_license': detect_driver_license_numbers,
        'inn': detect_inn_numbers,
        'full_name': detect_full_names,
        'birth_info': detect_birth_info,
        'address': detect_addresses,
        'phone': detect_phones,
        'email': detect_emails,
        'bank_details': detect_bank_details,
        'biometric': detect_biometric_data,
        'health': detect_health_data,
        'beliefs': detect_beliefs,
        'ethnicity': detect_ethnicity,
        # 'special_categories': detect_special_categories,
    }
    results = {}
    for category, detector in detectors.items():
        found = detector(text)
        if found:
            results[category] = found
    return results