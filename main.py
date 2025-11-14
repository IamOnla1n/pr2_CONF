#!/usr/bin/env python3
"""
Инструмент визуализации графа зависимостей пакетов Ubuntu
Этап 2: Сбор данных из официальных репозиториев Ubuntu
"""

import argparse
import sys
import os
import urllib.request
import gzip
import re
from typing import List, Dict


# === Функции валидации ===

def validate_package_name(name):
    """Валидация имени пакета Ubuntu"""
    if not name or not name.strip():
        raise ValueError("Имя пакета не может быть пустым")
    
    name = name.strip()
    # Проверка на допустимые символы для пакетов Ubuntu
    if not re.match(r'^[a-z0-9][a-z0-9.+-]*$', name):
        raise ValueError("Имя пакета содержит недопустимые символы")
    
    return name


def validate_url(url):
    """Валидация URL репозитория Ubuntu"""
    if not url or not url.strip():
        raise ValueError("URL репозитория не может быть пустым")

    url = url.strip()
    
    # Проверка официальных репозиториев Ubuntu
    official_repos = [
        'http://archive.ubuntu.com/ubuntu/',
        'http://ru.archive.ubuntu.com/ubuntu/',
        'https://archive.ubuntu.com/ubuntu/',
        'http://ports.ubuntu.com/ubuntu-ports/'
    ]
    
    if url in official_repos:
        return url
    
    # Проверка на корректность URL репозитория Ubuntu
    if not url.startswith(('http://', 'https://')):
        raise ValueError("URL должен начинаться с http:// или https://")
    
    if not url.endswith('/ubuntu/'):
        print(f"Предупреждение: URL '{url}' может не быть официальным репозиторием Ubuntu")
    
    return url


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
    # Проверка формата версии пакетов Ubuntu (например: 1.2.3-4ubuntu5)
    if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9.+:~-]*$', version):
        raise ValueError("Версия пакета содержит недопустимые символы")
    
    return version


# === Класс для работы с репозиториями Ubuntu ===

class UbuntuAPTRepository:
    """Класс для работы с официальными репозиториями пакетов Ubuntu APT"""
    
    def __init__(self, base_url: str = "http://archive.ubuntu.com/ubuntu/"):
        self.base_url = base_url.rstrip('/') + '/'
        self.packages_cache = {}
        
    def get_available_distributions(self) -> List[str]:
        """Получить список доступных дистрибутивов Ubuntu"""
        # Актуальные релизы Ubuntu
        return ["jammy", "focal", "bionic", "xenial", "trusty"]
    
    def get_packages_file_url(self, distribution: str = "jammy", component: str = "main", architecture: str = "amd64") -> str:
        """Сформировать URL для файла Packages.gz"""
        return f"{self.base_url}dists/{distribution}/{component}/binary-{architecture}/Packages.gz"
    
    def download_packages_index(self, distribution: str = "jammy", component: str = "main") -> Dict[str, Dict]:
        """Загрузить и распарсить индекс пакетов из репозитория"""
        packages_url = self.get_packages_file_url(distribution, component)
        
        print(f"Загрузка индекса пакетов из: {packages_url}")
        
        try:
            # Загрузка сжатого файла Packages.gz
            with urllib.request.urlopen(packages_url) as response:
                if response.status != 200:
                    raise Exception(f"HTTP ошибка: {response.status}")
                
                compressed_data = response.read()
            
            # Распаковка и декодирование
            packages_data = gzip.decompress(compressed_data).decode('utf-8', errors='ignore')
            
            # Парсинг данных пакетов
            packages = self._parse_packages_file(packages_data)
            print(f"Загружено информации о {len(packages)} пакетах из компонента {component}")
            
            return packages
            
        except urllib.error.URLError as e:
            raise Exception(f"Ошибка подключения к репозиторию: {e}")
        except Exception as e:
            raise Exception(f"Ошибка при загрузке индекса пакетов: {e}")
    
    def _parse_packages_file(self, packages_data: str) -> Dict[str, Dict]:
        """Парсинг файла Packages в формате Debian"""
        packages = {}
        current_package = {}
        current_key = None
        current_value = []
        
        lines = packages_data.split('\n')
        
        for line in lines:
            if line.strip() == '':
                # Конец описания пакета
                if current_package and 'Package' in current_package:
                    package_name = current_package['Package']
                    packages[package_name] = current_package.copy()
                current_package = {}
                current_key = None
                current_value = []
            elif line.startswith(' '):
                # Продолжение многострочного значения
                if current_key and current_value:
                    current_value.append(line.strip())
            else:
                # Новая строка ключ-значение
                if current_key and current_value:
                    current_package[current_key] = ' '.join(current_value)
                
                if ': ' in line:
                    key, value = line.split(': ', 1)
                    current_key = key
                    current_value = [value]
                else:
                    current_key = None
                    current_value = []
        
        # Добавляем последний пакет
        if current_package and 'Package' in current_package:
            package_name = current_package['Package']
            packages[package_name] = current_package.copy()
        
        return packages
    
    def find_package_version(self, package_name: str, version: str, packages_data: Dict) -> Dict:
        """Найти информацию о конкретной версии пакета"""
        if package_name not in packages_data:
            raise ValueError(f"Пакет '{package_name}' не найден в репозитории")
        
        package_info = packages_data[package_name]
        
        if version != 'latest':
            # Проверка соответствия версии
            if 'Version' in package_info and package_info['Version'] != version:
                print(f"Предупреждение: запрошенная версия {version} не совпадает с доступной {package_info.get('Version')}")
        
        return package_info
    
    def extract_dependencies(self, package_info: Dict) -> List[str]:
        """Извлечь прямые зависимости из информации о пакете"""
        dependencies = []
        
        # Обрабатываем основные поля зависимостей
        dependency_fields = ['Depends', 'Pre-Depends']
        
        for field in dependency_fields:
            if field in package_info:
                deps_text = package_info[field]
                # Парсим зависимости (игнорируя версии и альтернативы)
                deps = self._parse_dependency_field(deps_text)
                dependencies.extend(deps)
        
        # Убираем дубликаты
        return list(set(dependencies))
    
    def _parse_dependency_field(self, deps_text: str) -> List[str]:
        """Парсинг поля зависимостей в формате Debian"""
        dependencies = []
        
        # Разделяем по запятым
        for dep_block in deps_text.split(','):
            dep_block = dep_block.strip()
            if not dep_block:
                continue
            
            # Обрабатываем альтернативы (разделенные |)
            alternatives = dep_block.split('|')
            primary_alt = alternatives[0].strip()
            
            # Убираем информацию о версии (все что в скобках)
            if '(' in primary_alt:
                package_name = primary_alt.split('(')[0].strip()
            else:
                package_name = primary_alt
            
            # Убираем архитектурные ограничения
            if '[' in package_name:
                package_name = package_name.split('[')[0].strip()
            
            if package_name and package_name not in dependencies:
                dependencies.append(package_name)
        
        return dependencies


# === Основная логика сбора данных ===

def get_package_dependencies_ubuntu(package_name: str, version: str, repo_url: str, test_mode: bool = False) -> List[str]:
    """
    Основная функция для получения зависимостей пакета Ubuntu из официального репозитория
    
    Args:
        package_name: Имя пакета Ubuntu
        version: Версия пакета
        repo_url: URL репозитория Ubuntu
        test_mode: Режим тестирования
    
    Returns:
        List[str]: Список прямых зависимостей
    """
    print(f"\n=== Получение зависимостей для пакета Ubuntu '{package_name}' ===")
    print(f"Версия: {version}")
    print(f"Репозиторий: {repo_url}")
    
    if test_mode:
        print("РЕЖИМ ТЕСТИРОВАНИЯ: Используется тестовый репозиторий")
        # В тестовом режиме можно использовать локальные файлы
        return get_test_dependencies(package_name)
    
    try:
        # Создаем клиент для работы с репозиторием APT
        repo_client = UbuntuAPTRepository(repo_url)
        
        # Загружаем индекс пакетов из основных компонентов
        all_packages = {}
        components = ["main", "universe", "restricted", "multiverse"]
        
        for component in components:
            try:
                print(f"Загрузка пакетов из компонента: {component}")
                packages = repo_client.download_packages_index("jammy", component)
                all_packages.update(packages)
            except Exception as e:
                print(f"Не удалось загрузить компонент {component}: {e}")
                continue
        
        if not all_packages:
            raise Exception("Не удалось загрузить данные ни из одного компонента репозитория")
        
        # Ищем информацию о запрошенном пакете
        package_info = repo_client.find_package_version(package_name, version, all_packages)
        
        # Извлекаем зависимости
        dependencies = repo_client.extract_dependencies(package_info)
        
        # Выводим информацию о пакете
        print(f"\nИнформация о пакете '{package_name}':")
        print(f"  Версия: {package_info.get('Version', 'не указана')}")
        print(f"  Архитектура: {package_info.get('Architecture', 'не указана')}")
        print(f"  Раздел: {package_info.get('Section', 'не указан')}")
        print(f"  Описание: {package_info.get('Description', 'не указано')[:100]}...")
        
        return dependencies
        
    except Exception as e:
        raise Exception(f"Ошибка при получении зависимостей: {e}")


def get_test_dependencies(package_name: str) -> List[str]:
    """Функция для тестового режима с реальными данными зависимостей"""
    # Реальные зависимости популярных пакетов Ubuntu (для тестирования)
    real_dependencies = {
        "nginx": ["libc6", "libpcre3", "zlib1g", "libssl3", "adduser"],
        "python3": ["python3.10", "libpython3.10", "libc6", "libexpat1", "zlib1g"],
        "firefox": ["libgtk-3-0", "libdbus-glib-1-2", "libxt6", "libc6", "libstdc++6"],
        "vim": ["libc6", "libgpm2", "libselinux1", "libtinfo6", "libacl1"],
        "wget": ["libc6", "libssl3", "zlib1g", "libidn2-0"],
    }
    
    if package_name in real_dependencies:
        deps = real_dependencies[package_name]
    else:
        # Для неизвестных пакетов возвращаем базовые зависимости
        deps = ["libc6", "libgcc-s1", "libstdc++6"]
    
    print("ТЕСТОВЫЙ РЕЖИМ: Используются тестовые данные зависимостей")
    return deps


# === Основная функция ===

def main():
    parser = argparse.ArgumentParser(
        description='Инструмент визуализации графа зависимостей пакетов Ubuntu (Этап 2)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python main.py --package nginx --version 1.18.0 --output graph.png
  python main.py --package python3 --url http://archive.ubuntu.com/ubuntu/ --output deps.svg
  python main.py --package firefox --test-mode --output test.png
        """
    )

    # Обязательные параметры
    parser.add_argument('--package', 
                       type=validate_package_name, 
                       required=True, 
                       help='Имя анализируемого пакета Ubuntu (например: nginx, python3, firefox)')
    
    # Опциональные параметры
    parser.add_argument('--url', 
                       type=validate_url, 
                       default='http://archive.ubuntu.com/ubuntu/',
                       help='URL-адрес репозитория Ubuntu (по умолчанию: archive.ubuntu.com)')
    
    parser.add_argument('--test-mode', 
                       action='store_true', 
                       help='Режим работы с тестовым репозиторием')
    
    parser.add_argument('--version', 
                       type=validate_version, 
                       default='latest',
                       help='Версия пакета (по умолчанию: latest)')
    
    parser.add_argument('--output', 
                       type=validate_filename, 
                       default='dependency_graph.png',
                       help='Имя сгенерированного файла с изображением графа')

    try:
        args = parser.parse_args()

        # Вывод всех настраиваемых параметров в формате «ключ-значение»
        print("=== Настраиваемые параметры ===")
        print(f"Имя анализируемого пакета: {args.package}")
        print(f"URL-адрес репозитория: {args.url}")
        print(f"Режим работы с тестовым репозиторием: {'Включен' if args.test_mode else 'Выключен'}")
        print(f"Версия пакета: {args.version}")
        print(f"Имя сгенерированного файла: {args.output}")
        print("===============================")

        # Этап 2 — Сбор данных из репозитория Ubuntu APT
        dependencies = get_package_dependencies_ubuntu(
            package_name=args.package,
            version=args.version,
            repo_url=args.url,
            test_mode=args.test_mode
        )

        # Вывод прямых зависимостей (требование этапа 2)
        print(f"\n=== Прямые зависимости пакета '{args.package}' ===")
        if dependencies:
            for i, dep in enumerate(dependencies, 1):
                print(f"{i}. {dep}")
            print(f"\nВсего прямых зависимостей: {len(dependencies)}")
        else:
            print("Прямые зависимости не найдены")
        
        print("\nСбор данных завершён успешно. Можно переходить к этапу визуализации.")

    except Exception as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()