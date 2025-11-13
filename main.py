#!/usr/bin/env python3
"""
Инструмент визуализации графа зависимостей пакетов
Этап 2: Сбор данных
"""

import argparse
import sys
import os
import random


# === Этап 1: функции валидации ===

def validate_package_name(name):
    if not name or not name.strip():
        raise ValueError("Имя пакета не может быть пустым")
    if not all(c.isalnum() or c in '.-_' for c in name):
        raise ValueError("Имя пакета содержит недопустимые символы")
    return name.strip()


def validate_url(url):
    if not url or not url.strip():
        raise ValueError("URL или путь к файлу не может быть пустым")

    url = url.strip()
    if url.startswith(('http://', 'https://')):
        return url
    if os.path.exists(url):
        return url
    raise ValueError(f"Файл не существует: {url}")


def validate_filename(filename):
    if not filename or not filename.strip():
        raise ValueError("Имя файла не может быть пустым")

    filename = filename.strip()
    valid_extensions = ('.png', '.jpg', '.jpeg', '.svg', '.pdf')
    if not filename.lower().endswith(valid_extensions):
        raise ValueError(f"Неподдерживаемое расширение файла. Допустимые: {', '.join(valid_extensions)}")

    invalid_chars = '<>:"/\\|?*'
    if any(char in filename for char in invalid_chars):
        raise ValueError(f"Имя файла содержит недопустимые символы: {invalid_chars}")

    return filename


def validate_version(version):
    if not version or not version.strip():
        raise ValueError("Версия пакета не может быть пустой")
    version = version.strip()
    if not all(c.isalnum() or c in '.-+' for c in version):
        raise ValueError("Версия пакета содержит недопустимые символы")
    return version


# === Этап 2: Сбор данных ===

def simulate_dependency_data(package_name):
    """
    Имитация получения зависимостей для пакета (без обращения к сети).
    Генерирует фиктивные зависимости для демонстрации логики.
    """
    print(f"\n=== Получение зависимостей для пакета '{package_name}' ===")

    # Список возможных "библиотек"
    sample_libs = [
        "libc6", "libffi", "libssl", "zlib", "requests",
        "numpy-base", "setuptools", "wheel", "certifi", "pandas"
    ]

    # Фиксированные зависимости для популярных пакетов
    known_packages = {
        "numpy": ["libc6", "libffi"],
        "pandas": ["numpy", "python-dateutil", "pytz"],
        "requests": ["urllib3", "certifi", "chardet"],
        "matplotlib": ["numpy", "pillow", "cycler"],
    }

    if package_name in known_packages:
        deps = known_packages[package_name]
    else:
        deps = random.sample(sample_libs, k=random.randint(1, 4))

    print(" Найдены прямые зависимости:")
    for dep in deps:
        print(f"  - {dep}")

    return deps


# === Основная функция ===

def main():
    parser = argparse.ArgumentParser(
        description='Инструмент визуализации графа зависимостей пакетов (Этап 2)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
python main.py --package numpy --url https://pypi.org --version 1.24.0 --output graph.png
python main.py --package requests --url https://pypi.org --output test.png
        """
    )

    parser.add_argument('--package', type=validate_package_name, required=True, help='Имя анализируемого пакета')
    parser.add_argument('--url', type=validate_url, required=True, help='URL репозитория или путь к файлу')
    parser.add_argument('--test-mode', action='store_true', help='Режим тестового репозитория')
    parser.add_argument('--version', type=validate_version, default='latest', help='Версия пакета')
    parser.add_argument('--output', type=validate_filename, default='dependency_graph.png', help='Имя выходного файла')

    try:
        args = parser.parse_args()

        # Вывод конфигурации
        print("=== Параметры конфигурации ===")
        print(f"Анализируемый пакет: {args.package}")
        print(f"URL/путь к репозиторию: {args.url}")
        print(f"Режим тестового репозитория: {'Включен' if args.test_mode else 'Выключен'}")
        print(f"Версия пакета: {args.version}")
        print(f"Выходной файл: {args.output}")
        print("==============================")

        # Этап 2 — Сбор данных
        deps = simulate_dependency_data(args.package)

        print("\n=== Результаты этапа 2 ===")
        print(f"Количество прямых зависимостей: {len(deps)}")
        print("Сбор данных завершён успешно. Можно переходить к этапу 3.")

    except Exception as e:
        print(f" Ошибка: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
