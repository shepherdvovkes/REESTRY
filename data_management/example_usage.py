#!/usr/bin/env python3
"""
Примеры использования модулей управления данными
"""
import logging
from data_management import (
    DatabaseManager,
    DataIntegrityChecker,
    IntegrityMonitor,
    DataDownloadManager,
    MLDatasetManager
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# Инициализация менеджера БД
db = DatabaseManager(
    host='localhost',
    port=5432,
    database='reestry',
    user='reestry_user',
    password='reestry_password'
)


def example_1_register_and_download():
    """Пример 1: Регистрация источника и загрузка данных"""
    print("\n" + "="*60)
    print("Пример 1: Регистрация источника и загрузка данных")
    print("="*60)
    
    download_manager = DataDownloadManager(db)
    
    # Регистрация нового источника
    source_id = download_manager.register_source(
        url='https://data.gov.ua/api/dataset/example',
        source_type='api',
        metadata={
            'auth': {'api_key': 'your-api-key'},
            'pagination_params': {'offset': 'offset', 'limit': 'limit'}
        }
    )
    
    print(f"✅ Зарегистрирован источник с ID: {source_id}")
    
    # Загрузка данных с возможностью возобновления
    try:
        download_manager.resume_download(source_id, batch_size=100)
        print(f"✅ Загрузка завершена для источника {source_id}")
    except Exception as e:
        print(f"❌ Ошибка загрузки: {e}")
        print(f"💡 Можно возобновить загрузку позже: download_manager.resume_download({source_id})")


def example_2_check_integrity():
    """Пример 2: Проверка целостности данных"""
    print("\n" + "="*60)
    print("Пример 2: Проверка целостности данных")
    print("="*60)
    
    checker = DataIntegrityChecker(db)
    
    # Проверка конкретного источника
    source_id = 1  # ID источника
    result = checker.verify_downloaded_data(source_id)
    
    print(f"Результаты проверки источника {source_id}:")
    print(f"  - Целостность: {result['integrity_score']:.2%}")
    print(f"  - Исходных записей: {result['total_original']}")
    print(f"  - Загружено записей: {result['total_downloaded']}")
    print(f"  - Отсутствующих: {len(result['missing_records'])}")
    print(f"  - Несовпадающих: {len(result['mismatched_records'])}")
    print(f"  - Лишних: {len(result['extra_records'])}")
    
    if result['integrity_score'] < 0.99:
        print("⚠️  Обнаружены проблемы с целостностью данных!")


def example_3_monitor_integrity():
    """Пример 3: Мониторинг целостности всех источников"""
    print("\n" + "="*60)
    print("Пример 3: Мониторинг целостности всех источников")
    print("="*60)
    
    checker = DataIntegrityChecker(db)
    monitor = IntegrityMonitor(db, checker)
    
    # Проверка всех источников
    results = monitor.verify_all_sources()
    
    print(f"\nПроверено источников: {len(results)}")
    for result in results:
        status_icon = "✅" if result['status'] == 'ok' else "⚠️" if result['status'] == 'warning' else "❌"
        print(f"{status_icon} {result['source_url']}: {result.get('integrity_score', 'N/A')}")


def example_4_create_dataset():
    """Пример 4: Создание датасета для ML обучения"""
    print("\n" + "="*60)
    print("Пример 4: Создание датасета для ML обучения")
    print("="*60)
    
    dataset_manager = MLDatasetManager(db)
    
    # Создание базовой версии датасета
    version_id = dataset_manager.create_dataset_version(
        name='ukrainian_laws_v1',
        description='Базовый датасет украинских законов'
    )
    
    print(f"✅ Создана версия датасета: {version_id}")
    
    # Подготовка датасета
    result = dataset_manager.prepare_training_dataset(
        version_id=version_id,
        filters={'document_type': 'Кодекс'},
        min_length=1000
    )
    
    print(f"✅ Подготовлен датасет:")
    print(f"   - Образцов: {result['total_samples']}")
    print(f"   - Размер: {result['size_mb']:.2f} MB")
    
    # Экспорт для обучения
    export_file = dataset_manager.export_for_training(
        version_id=version_id,
        format='jsonl',
        output_file='training_data.jsonl'
    )
    print(f"✅ Экспортировано в: {export_file}")


def example_5_incremental_dataset():
    """Пример 5: Создание инкрементального датасета"""
    print("\n" + "="*60)
    print("Пример 5: Создание инкрементального датасета")
    print("="*60)
    
    dataset_manager = MLDatasetManager(db)
    
    # Базовая версия
    base_version_id = 1
    
    # Получение инкрементальных обновлений
    new_samples = dataset_manager.get_incremental_updates(base_version_id)
    
    print(f"Найдено новых/измененных документов: {len(new_samples)}")
    
    if len(new_samples) >= 100:  # Минимальный порог для создания инкрементального датасета
        # Создание инкрементального датасета
        new_version_id = dataset_manager.create_incremental_dataset(
            base_version_id=base_version_id,
            new_samples=new_samples
        )
        
        print(f"✅ Создана инкрементальная версия: {new_version_id}")
        print(f"   - Новых образцов: {len(new_samples)}")
        
        # Экспорт для дообучения
        export_file = dataset_manager.export_for_training(
            version_id=new_version_id,
            format='jsonl',
            output_file=f'incremental_{new_version_id}.jsonl'
        )
        print(f"✅ Экспортировано в: {export_file}")
    else:
        print(f"⚠️  Недостаточно новых данных для инкрементального датасета "
              f"(минимум 100, найдено {len(new_samples)})")


if __name__ == '__main__':
    print("Примеры использования модулей управления данными")
    print("="*60)
    
    try:
        # Раскомментируйте нужные примеры
        
        # example_1_register_and_download()
        # example_2_check_integrity()
        # example_3_monitor_integrity()
        # example_4_create_dataset()
        # example_5_incremental_dataset()
        
        print("\n💡 Раскомментируйте нужные примеры в коде для запуска")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

