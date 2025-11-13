#!/usr/bin/env python3
"""
Инструмент визуализации графа зависимостей пакетов
Этап 3: Основные операции
"""

import argparse
import sys
import os
import random
from collections import defaultdict


# === Валидация параметров ===

def validate_package_name(name):
    if not name or not name.strip():
        raise ValueError("Имя пакета не может быть пустым")
    if not all(c.isalnum() or c in '.-_' for c in name):
        raise ValueError("Имя пакета содержит недопустимые символы")
    return name.strip()


def validate_url(url, test_mode=False):
    """Валидация URL или пути к файлу"""
    if not url or not url.strip():
        raise ValueError("URL или путь к файлу не может быть пустым")

    url = url.strip()

    # Проверка на URL
    if url.startswith(('http://', 'https://')):
        return url

    # Проверка пути к файлу (в тестовом режиме файл может отсутствовать)
    if os.path.exists(url) or test_mode:
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


# === Логика этапа 3 ===

def simulate_dependency_data(package_name):
    """Имитация получения зависимостей для пакета"""
    known_packages = {
        "C": ["A", "B"],
        "E": ["C", "D", "E"],
        "F": ["G", "J", "K"],
        "L": ["C", "M", "N"],
    }

    sample_libs = [
        "A", "B", "O", "P", "F",
        "Q", "R", "S", "T", "E"
    ]

    if package_name in known_packages:
        return known_packages[package_name]
    else:
        return random.sample(sample_libs, k=random.randint(1, 3))


def load_test_graph(file_path):
    """Загрузка тестового графа зависимостей из файла (режим тестирования)"""
    graph = defaultdict(list)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or ':' not in line:
                    continue
                pkg, deps = line.split(':')
                pkg = pkg.strip()
                dep_list = [d.strip() for d in deps.split(',') if d.strip()]
                graph[pkg] = dep_list
        return graph
    except Exception as e:
        print(f"Ошибка при чтении тестового файла: {e}")
        sys.exit(1)


def build_dependency_graph(package, test_mode=False, url=None):
    """Построение графа зависимостей с помощью BFS и рекурсии"""
    visited = set()
    graph = defaultdict(list)

    if test_mode and url and os.path.exists(url):
        test_graph = load_test_graph(url)
    else:
        test_graph = {}

    def bfs(pkg):
        if pkg in visited:
            return
        visited.add(pkg)
        if test_mode and test_graph:
            deps = test_graph.get(pkg, [])
        else:
            deps = simulate_dependency_data(pkg)
        graph[pkg] = deps
        for dep in deps:
            if dep not in visited:
                bfs(dep)

    bfs(package)
    return graph


def detect_cycles(graph):
    """Проверка наличия циклов"""
    visited = set()
    stack = set()

    def dfs(node):
        if node in stack:
            return True
        if node in visited:
            return False
        visited.add(node)
        stack.add(node)
        for neighbor in graph.get(node, []):
            if dfs(neighbor):
                return True
        stack.remove(node)
        return False

    for node in graph:
        if dfs(node):
            return True
    return False


def print_graph(graph):
    """Вывод графа зависимостей"""
    print("\n=== Граф зависимостей ===")
    for pkg, deps in graph.items():
        deps_str = ", ".join(deps) if deps else "(нет зависимостей)"
        print(f"{pkg} -> {deps_str}")


# === Основная функция ===

def main():
    parser = argparse.ArgumentParser(
        description='Инструмент визуализации графа зависимостей пакетов (Этап 3)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
python main.py --package numpy --url https://pypi.org --version 1.24.0 --output graph.png
python main.py --package A --url ./test_graph.txt --test-mode --output graph.svg
        """
    )

    parser.add_argument('--package', type=validate_package_name, required=True, help='Имя анализируемого пакета')
    parser.add_argument('--url', required=True, help='URL репозитория или путь к файлу')
    parser.add_argument('--test-mode', action='store_true', help='Режим тестового репозитория')
    parser.add_argument('--version', type=validate_version, default='latest', help='Версия пакета')
    parser.add_argument('--output', type=validate_filename, default='dependency_graph.png', help='Имя выходного файла')

    try:
        args = parser.parse_args()

        # Проверка URL с учётом test_mode
        args.url = validate_url(args.url, test_mode=args.test_mode)

        print("=== Параметры конфигурации ===")
        print(f"Анализируемый пакет: {args.package}")
        print(f"URL/путь к репозиторию: {args.url}")
        print(f"Режим тестового репозитория: {'Включен' if args.test_mode else 'Выключен'}")
        print(f"Версия пакета: {args.version}")
        print(f"Выходной файл: {args.output}")
        print("==============================")

        graph = build_dependency_graph(args.package, test_mode=args.test_mode, url=args.url)

        if detect_cycles(graph):
            print("\n Обнаружены циклические зависимости!")
        else:
            print("\n Циклических зависимостей не найдено.")

        print_graph(graph)
        print("\nГраф зависимостей успешно построен.")

    except Exception as e:
        print(f" Ошибка: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
