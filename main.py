#!/usr/bin/env python3
"""
Инструмент визуализации графа зависимостей пакетов Ubuntu
Этап 3: Основные операции - построение графа зависимостей с учетом транзитивности
"""

import argparse
import sys
import os
import urllib.request
import gzip
import re
from typing import List, Dict, Set
from collections import deque


# === Функции валидации ===

def validate_package_name(name):
    """Валидация имени пакета"""
    if not name or not name.strip():
        raise ValueError("Имя пакета не может быть пустым")
    
    name = name.strip()
    # Принимаем как пакеты Ubuntu (нижний регистр), так и тестовые (верхний регистр)
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
        """Извлечь прямые зависимости из информации о пакете"""
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
    Построение графа зависимостей с помощью алгоритм BFS с рекурсией
    
    Args:
        start_package: начальный пакет
        get_dependencies_func: функция для получения зависимостей пакета
        max_depth: максимальная глубина рекурсии
    
    Returns:
        Dict[str, List[str]]: граф зависимостей
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
            
            print(f"{'  ' * depth}Пакет: {current_package}, зависимости: {dependencies}")
            
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
    
    Returns:
        Dict[str, List[str]]: граф зависимостей
    """
    print(f"\n=== Получение графа зависимостей для пакета '{package_name}' ===")
    print(f"Версия: {version}")
    print(f"Источник: {repo_url}")
    print(f"Режим тестирования: {'Включен' if test_mode else 'Выключен'}")
    
    get_deps_func = get_dependencies_func_factory(repo_url, test_mode)
    
    # Строим полный граф зависимостей с помощью BFS с рекурсией
    dependency_graph = build_dependency_graph_bfs(package_name, get_deps_func)
    
    return dependency_graph


# === Основная функция ===

def main():
    parser = argparse.ArgumentParser(
        description='Инструмент визуализации графа зависимостей пакетов Ubuntu (Этап 3)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  # Реальный репозиторий Ubuntu
  python main.py --package nginx --url http://archive.ubuntu.com/ubuntu/ --output graph.png
  
  # Тестовый репозиторий с файлом
  python main.py --package A --url test_repo.txt --test-mode --output deps.svg
  
  # С указанием версии
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

    try:
        args = parser.parse_args()

        # Вывод параметров конфигурации
        print("=== Параметры конфигурации ===")
        print(f"Анализируемый пакет: {args.package}")
        print(f"URL/путь к репозиторию: {args.url}")
        print(f"Режим тестового репозитория: {'Включен' if args.test_mode else 'Выключен'}")
        print(f"Версия пакета: {args.version}")
        print(f"Выходной файл: {args.output}")
        print("==============================")

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
        
        print("\nПостроение графа зависимостей завершено успешно.")

    except Exception as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()