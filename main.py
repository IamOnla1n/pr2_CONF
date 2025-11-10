#!/usr/bin/env python3
"""
Минимальное CLI-приложение для визуализации графа зависимостей пакетов
Этап 1: Минимальный прототип с конфигурацией
"""

import argparse
import sys
import os


def validate_package_name(name):
    """Валидация имени пакета"""
    if not name or not name.strip():
        raise ValueError("Имя пакета не может быть пустым")
    if not all(c.isalnum() or c in '.-_' for c in name):
        raise ValueError("Имя пакета содержит недопустимые символы")
    return name.strip()


def validate_url(url):
    """Валидация URL или пути к файлу"""
    if not url or not url.strip():
        raise ValueError("URL или путь к файлу не может быть пустым")
    
    url = url.strip()
    
    # Проверка на URL
    if url.startswith(('http://', 'https://')):
        return url
    
    # Проверка на путь к файлу
    if os.path.exists(url):
        return url
    else:
        raise ValueError(f"Файл не существует: {url}")


def validate_filename(filename):
    """Валидация имени файла для изображения"""
    if not filename or not filename.strip():
        raise ValueError("Имя файла не может быть пустым")
    
    filename = filename.strip()
    
    # Проверяем расширение файла
    valid_extensions = ('.png', '.jpg', '.jpeg', '.svg', '.pdf')
    if not filename.lower().endswith(valid_extensions):
        raise ValueError(f"Неподдерживаемое расширение файла. Допустимые: {', '.join(valid_extensions)}")
    
    # Проверяем допустимость символов в имени файла
    invalid_chars = '<>:"/\\|?*'
    if any(char in filename for char in invalid_chars):
        raise ValueError(f"Имя файла содержит недопустимые символы: {invalid_chars}")
    
    return filename


def validate_version(version):
    """Валидация версии пакета"""
    if not version or not version.strip():
        raise ValueError("Версия пакета не может быть пустой")
    
    version = version.strip()
    
    # Простая проверка формата версии (может быть расширена)
    if not all(c.isalnum() or c in '.-+' for c in version):
        raise ValueError("Версия пакета содержит недопустимые символы")
    
    return version


def main():   


    
    """Основная функция приложения"""
    parser = argparse.ArgumentParser(
        description='Инструмент визуализации графа зависимостей пакетов',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
python src/main.py --package numpy --url https://pypi.org --version 1.24.0 --output graph.png
python src/main.py --package requests --url ./test_repo.json --test-mode --output deps.svg
        """
    )
    
    # Обязательные параметры
    parser.add_argument(
        '--package',
        type=validate_package_name,
        required=True,
        help='Имя анализируемого пакета'
    )
    
    parser.add_argument(
        '--url',
        type=validate_url,
        required=True,
        help='URL-адрес репозитория или путь к файлу тестового репозитория'
    )
    
    # Опциональные параметры
    parser.add_argument(
        '--test-mode',
        action='store_true',
        help='Режим работы с тестовым репозиторием'
    )
    
    parser.add_argument(
        '--version',
        type=validate_version,
        default='latest',
        help='Версия пакета (по умолчанию: latest)'
    )
    
    parser.add_argument(
        '--output',
        type=validate_filename,
        default='dependency_graph.png',
        help='Имя сгенерированного файла с изображением графа (по умолчанию: dependency_graph.png)'
    )
    
    try:
        args = parser.parse_args()
        
        # Вывод всех параметров в формате ключ-значение
        print("=== Параметры конфигурации ===")
        print(f"Анализируемый пакет: {args.package}")
        print(f"URL/путь к репозиторию: {args.url}")
        print(f"Режим тестового репозитория: {'Включен' if args.test_mode else 'Выключен'}")
        print(f"Версия пакета: {args.version}")
        print(f"Выходной файл: {args.output}")
        print("==============================")
        
        # Здесь будет основная логика приложения на следующих этапах
        print("\nКонфигурация успешно загружена. Готово к анализу зависимостей!")
        
    except argparse.ArgumentError as e:
        print(f"Ошибка в аргументах командной строки: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Ошибка валидации параметров: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Неожиданная ошибка: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()