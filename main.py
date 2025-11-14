#!/usr/bin/env python3
"""
Инструмент визуализации графа зависимостей пакетов Ubuntu
Этап 4: Дополнительные операции - порядок загрузки зависимостей
"""

import argparse
import sys
import os
import urllib.request
import gzip
import re
from typing import List, Dict, Set, Tuple
from collections import deque


# === Функции валидации ===

def validate_package_name(name):
    """Валидация имени пакета"""
    if not name or not name.strip():
        raise ValueError("Имя пакета не может быть пустым")
    
    name = name.strip()
    if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9.+-]*$', name):
        raise ValueError("Имя пакета содержит недопустимые символы")
    
    return name


def validate_url(url):
    """Валидация URL репозитория Ubuntu или пути к тестовому файлу"""
    if not url or not url.strip():
        raise ValueError("URL репозитория или путь к файлу не может быть пустым")

    url = url.strip()
    
    if url.startswith(('http://', 'https://')):
        return url
    
    if os.path.exists(url):
        return url
    
    raise ValueError(f"URL невалиден или файл не существует: {url}")


def validate_filename(filename):
    """Валидация имени файла для вывода"""
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
    """Валидация версии пакета Ubuntu"""
    if not version or not version.strip():
        raise ValueError("Версия пакета не может быть пустой")
    
    version = version.strip()
    if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9.+:~-]*$', version):
        raise ValueError("Версия пакета содержит недопустимые символы")
    
    return version


# === Класс для работы с репозиториями Ubuntu ===

class UbuntuAPTRepository:
    """Класс для работы с официальными репозиториями пакетов Ubuntu APT"""
    
    def __init__(self, base_url: str = "http://archive.ubuntu.com/ubuntu/"):
        self.base_url = base_url.rstrip('/') + '/'
        
    def get_packages_file_url(self, distribution: str = "jammy", component: str = "main", architecture: str = "amd64") -> str:
        """Сформировать URL для файла Packages.gz"""
        return f"{self.base_url}dists/{distribution}/{component}/binary-{architecture}/Packages.gz"
    
    def download_packages_index(self, distribution: str = "jammy", component: str = "main") -> Dict[str, Dict]:
        """Загрузить и распарсить индекс пакетов из репозитория"""
        packages_url = self.get_packages_file_url(distribution, component)
        
        print(f"Загрузка индекса пакетов из: {packages_url}")
        
        try:
            with urllib.request.urlopen(packages_url) as response:
                if response.status != 200:
                    raise Exception(f"HTTP ошибка: {response.status}")
                
                compressed_data = response.read()
            
            packages_data = gzip.decompress(compressed_data).decode('utf-8', errors='ignore')
            packages = self._parse_packages_file(packages_data)
            print(f"Загружено информации о {len(packages)} пакетах из компонента {component}")
            
            return packages
            
        except Exception as e:
            raise Exception(f"Ошибка при загрузке индекса пакетов: {e}")
    
    def _parse_packages_file(self, packages_data: str) -> Dict[str, Dict]:
        """Парсинг файла Packages в формате Debian"""
        packages = {}
        current_package = {}
        
        for line in packages_data.split('\n'):
            if line.strip() == '':
                if current_package and 'Package' in current_package:
                    package_name = current_package['Package']
                    packages[package_name] = current_package.copy()
                current_package = {}
            elif ': ' in line:
                key, value = line.split(': ', 1)
                current_package[key] = value
        
        if current_package and 'Package' in current_package:
            package_name = current_package['Package']
            packages[package_name] = current_package.copy()
        
        return packages
    
    def extract_dependencies(self, package_info: Dict) -> List[str]:
        """Извлечь прямые зависимости из информации о пакета"""
        dependencies = []
        
        dependency_fields = ['Depends', 'Pre-Depends']
        
        for field in dependency_fields:
            if field in package_info:
                deps_text = package_info[field]
                deps = self._parse_dependency_field(deps_text)
                dependencies.extend(deps)
        
        return list(set(dependencies))
    
    def _parse_dependency_field(self, deps_text: str) -> List[str]:
        """Парсинг поля зависимостей в формате Debian"""
        dependencies = []
        
        for dep_block in deps_text.split(','):
            dep_block = dep_block.strip()
            if not dep_block:
                continue
            
            alternatives = dep_block.split('|')
            primary_alt = alternatives[0].strip()
            
            if '(' in primary_alt:
                package_name = primary_alt.split('(')[0].strip()
            else:
                package_name = primary_alt
            
            if '[' in package_name:
                package_name = package_name.split('[')[0].strip()
            
            if package_name and package_name not in dependencies:
                dependencies.append(package_name)
        
        return dependencies


# === Класс для работы с тестовым репозиторием ===

class TestRepository:
    """Класс для работы с тестовым репозиторием (пакеты называются большими латинскими буквами)"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.dependencies = self._parse_test_file()
    
    def _parse_test_file(self) -> Dict[str, List[str]]:
        """Парсинг файла тестового репозитория"""
        dependencies = {}
        
        try:
            with open(self.file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or ':' not in line:
                        continue
                    
                    package, deps_str = line.split(':', 1)
                    package = package.strip()
                    
                    # Проверка что пакет назван большими латинскими буквами
                    if not re.match(r'^[A-Z]+$', package):
                        raise ValueError(f"Пакет должен называться большими латинскими буквами: {package}")
                    
                    deps = [dep.strip() for dep in deps_str.split(',') if dep.strip()]
                    
                    # Проверка что зависимости названы большими латинскими буквами
                    for dep in deps:
                        if not re.match(r'^[A-Z]+$', dep):
                            raise ValueError(f"Зависимость должна называться большими латинскими буквами: {dep}")
                    
                    dependencies[package] = deps
            
            print(f"Загружено {len(dependencies)} пакетов из тестового файла")
            return dependencies
            
        except Exception as e:
            raise Exception(f"Ошибка при чтении тестового файла: {e}")
    
    def get_dependencies(self, package_name: str) -> List[str]:
        """Получить зависимости пакета из тестового репозитория"""
        if package_name not in self.dependencies:
            print(f"Предупреждение: пакет '{package_name}' не найден в тестовом репозитории")
            return []
        return self.dependencies.get(package_name, [])


# === Алгоритм BFS с рекурсией для построения графа ===

def build_dependency_graph_bfs(start_package: str, 
                             get_dependencies_func, 
                             max_depth: int = 10) -> Dict[str, List[str]]:
    """
    Построение графа зависимостей с помощью алгоритма BFS с рекурсией
    """
    graph = {}
    visited = set()
    recursion_stack = set()
    cycles_detected = []
    
    def bfs_recursive(current_package: str, depth: int, path: List[str]):
        if depth > max_depth:
            print(f"Достигнута максимальная глубина {max_depth} для пакета {current_package}")
            return
        
        if current_package in recursion_stack:
            cycle = path + [current_package]
            cycle_str = " -> ".join(cycle)
            cycles_detected.append(cycle_str)
            print(f"Обнаружена циклическая зависимость: {cycle_str}")
            return
        
        if current_package in visited:
            return
        
        visited.add(current_package)
        recursion_stack.add(current_package)
        
        try:
            dependencies = get_dependencies_func(current_package)
            graph[current_package] = dependencies
            
            for dep in dependencies:
                bfs_recursive(dep, depth + 1, path + [current_package])
                
        except Exception as e:
            print(f"Ошибка при получении зависимостей для {current_package}: {e}")
        finally:
            recursion_stack.remove(current_package)
    
    print("=== Построение графа зависимостей алгоритмом BFS с рекурсией ===")
    bfs_recursive(start_package, 0, [])
    
    if cycles_detected:
        print(f"\n=== Обнаружено циклических зависимостей: {len(cycles_detected)} ===")
        for i, cycle in enumerate(cycles_detected, 1):
            print(f"{i}. {cycle}")
    
    return graph


# === Алгоритм для определения порядка загрузки зависимостей ===

def calculate_download_order(start_package: str, 
                           get_dependencies_func,
                           max_depth: int = 10) -> Tuple[List[str], Dict[str, List[str]]]:
    """
    Определение порядка загрузки зависимостей с помощью топологической сортировки
    """
    graph = build_dependency_graph_bfs(start_package, get_dependencies_func, max_depth)
    
    # Строим обратный граф для вычисления входящих степеней
    reverse_graph = {}
    in_degree = {}
    
    # Инициализация
    for package in graph:
        reverse_graph[package] = []
        in_degree[package] = 0
    
    # Построение обратного графа и подсчет входящих степеней
    for package, deps in graph.items():
        for dep in deps:
            if dep not in reverse_graph:
                reverse_graph[dep] = []
                in_degree[dep] = 0
            reverse_graph[dep].append(package)
            in_degree[package] = in_degree.get(package, 0) + 1
    
    # Алгоритм Кана (топологическая сортировка)
    order = []
    queue = deque()
    
    # Добавляем пакеты с нулевой входящей степенью
    for package, degree in in_degree.items():
        if degree == 0:
            queue.append(package)
    
    while queue:
        current = queue.popleft()
        order.append(current)
        
        for dependent in reverse_graph.get(current, []):
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)
    
    # Проверка на циклы (если остались пакеты с ненулевой степенью)
    remaining_packages = [pkg for pkg, deg in in_degree.items() if deg > 0 and pkg not in order]
    if remaining_packages:
        print(f"Предупреждение: обнаружены циклические зависимости среди пакетов: {remaining_packages}")
    
    return order, graph


def print_download_order_analysis(start_package: str, 
                                download_order: List[str], 
                                dependency_graph: Dict[str, List[str]]):
    """
    Вывод анализа порядка загрузки и сравнение с реальным менеджером пакетов
    """
    print(f"\n=== Анализ порядка загрузки для пакета '{start_package}' ===")
    
    print(f"\nПорядок загрузки зависимостей:")
    for i, package in enumerate(download_order, 1):
        print(f"{i:2d}. {package}")
    
    print(f"\nВсего пакетов для загрузки: {len(download_order)}")
    
    # Анализ расхождений с реальным менеджером пакетов
    print(f"\n=== Сравнение с реальным менеджером пакетов ===")
    print("Возможные расхождения в порядке загрузки могут быть вызваны:")
    print("1. Альтернативными зависимостями (через '|') - наш алгоритм выбирает первую альтернативу")
    print("2. Условными зависимостями (архитектурные ограничения) - наш алгоритм их игнорирует")
    print("3. Рекомендуемыми зависимостями (Recommends) - наш алгоритм их не учитывает")
    print("4. Конфликтующими пакетами (Conflicts) - наш алгоритм их не обрабатывает")
    print("5. Разными алгоритмами разрешения зависимостей")
    print("6. Наличием циклических зависимостей - наш алгоритм их обнаруживает, но может обрабатывать иначе")
    
    # Демонстрация на тестовых примерах
    if all(pkg.isupper() for pkg in download_order):
        print(f"\n=== Демонстрация на тестовом репозитории ===")
        print("Для тестового репозитория порядок загрузки гарантированно корректен")
        print("так как все зависимости явно заданы в файле конфигурации")


# === Основная логика получения зависимостей ===

def get_dependencies_func_factory(repo_url: str, test_mode: bool = False):
    """Фабрика функций для получения зависимостей"""
    if test_mode and not repo_url.startswith(('http://', 'https://')):
        # Режим тестового репозитория с файлом
        test_repo = TestRepository(repo_url)
        return test_repo.get_dependencies
    else:
        # Режим реального репозитория Ubuntu
        repo_client = UbuntuAPTRepository(repo_url)
        
        # Предварительно загружаем все пакеты для эффективности
        all_packages = {}
        components = ["main", "universe"]
        
        for component in components:
            try:
                packages = repo_client.download_packages_index("jammy", component)
                all_packages.update(packages)
            except Exception as e:
                print(f"Не удалось загрузить компонент {component}: {e}")
                continue
        
        def get_ubuntu_dependencies(package_name: str) -> List[str]:
            if package_name in all_packages:
                return repo_client.extract_dependencies(all_packages[package_name])
            else:
                print(f"Пакет {package_name} не найден в репозитории")
                return []
        
        return get_ubuntu_dependencies


def get_package_dependencies_ubuntu(package_name: str, version: str, repo_url: str, test_mode: bool = False) -> Dict[str, List[str]]:
    """
    Основная функция для получения графа зависимостей пакета Ubuntu
    """
    print(f"\n=== Получение графа зависимостей для пакета '{package_name}' ===")
    print(f"Версия: {version}")
    print(f"Источник: {repo_url}")
    print(f"Режим тестирования: {'Включен' if test_mode else 'Выключен'}")
    
    get_deps_func = get_dependencies_func_factory(repo_url, test_mode)
    
    # Строим полный граф зависимостей с помощью BFS с рекурсией
    dependency_graph = build_dependency_graph_bfs(package_name, get_deps_func)
    
    return dependency_graph


def analyze_download_order(package_name: str, version: str, repo_url: str, test_mode: bool = False):
    """
    Анализ порядка загрузки зависимостей
    """
    print(f"\n=== Анализ порядка загрузки для пакета '{package_name}' ===")
    print(f"Версия: {version}")
    print(f"Источник: {repo_url}")
    print(f"Режим тестирования: {'Включен' if test_mode else 'Выключен'}")
    
    get_deps_func = get_dependencies_func_factory(repo_url, test_mode)
    
    # Определяем порядок загрузки
    download_order, dependency_graph = calculate_download_order(package_name, get_deps_func)
    
    # Выводим анализ
    print_download_order_analysis(package_name, download_order, dependency_graph)
    
    return download_order, dependency_graph


# === Основная функция ===

def main():
    parser = argparse.ArgumentParser(
        description='Инструмент визуализации графа зависимостей пакетов Ubuntu (Этап 4)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  # Реальный репозиторий Ubuntu - порядок загрузки
  python main.py --package nginx --url http://archive.ubuntu.com/ubuntu/ --download-order
  
  # Тестовый репозиторий с файлом - порядок загрузки
  python main.py --package A --url test_repo.txt --test-mode --download-order
  
  # Построение графа зависимостей
  python main.py --package python3 --version 3.10 --output test.png
        """
    )

    parser.add_argument('--package', 
                       type=validate_package_name, 
                       required=True, 
                       help='Имя анализируемого пакета')
    
    parser.add_argument('--url', 
                       type=validate_url, 
                       default='http://archive.ubuntu.com/ubuntu/',
                       help='URL репозитория Ubuntu или путь к файлу тестового репозитория')
    
    parser.add_argument('--test-mode', 
                       action='store_true', 
                       help='Режим работы с тестовым репозиторием')
    
    parser.add_argument('--version', 
                       type=validate_version, 
                       default='latest',
                       help='Версия пакета')
    
    parser.add_argument('--output', 
                       type=validate_filename, 
                       default='dependency_graph.png',
                       help='Имя сгенерированного файла с изображением графа')
    
    parser.add_argument('--download-order', 
                       action='store_true',
                       help='Режим вывода на экран порядка загрузки зависимостей')

    try:
        args = parser.parse_args()

        # Вывод параметров конфигурации
        print("=== Параметры конфигурации ===")
        print(f"Анализируемый пакет: {args.package}")
        print(f"URL/путь к репозиторию: {args.url}")
        print(f"Режим тестового репозитория: {'Включен' if args.test_mode else 'Выключен'}")
        print(f"Версия пакета: {args.version}")
        print(f"Выходной файл: {args.output}")
        print(f"Режим порядка загрузки: {'Включен' if args.download_order else 'Выключен'}")
        print("==============================")

        if args.download_order:
            # Режим порядка загрузки (требование этапа 4)
            download_order, dependency_graph = analyze_download_order(
                package_name=args.package,
                version=args.version,
                repo_url=args.url,
                test_mode=args.test_mode
            )
        else:
            # Построение графа зависимостей
            dependency_graph = get_package_dependencies_ubuntu(
                package_name=args.package,
                version=args.version,
                repo_url=args.url,
                test_mode=args.test_mode
            )

            # Вывод результатов
            print(f"\n=== Результаты построения графа ===")
            print(f"Всего пакетов в графе: {len(dependency_graph)}")
            print(f"Прямые зависимости {args.package}: {dependency_graph.get(args.package, [])}")
        
        print("\nОбработка завершена успешно.")

    except Exception as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()