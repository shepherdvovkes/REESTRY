"""
Модуль для управления датасетами ML обучения
"""
from datetime import datetime
from typing import List, Dict, Optional
import json
import hashlib
import logging

from .database import DatabaseManager

logger = logging.getLogger(__name__)


class MLDatasetManager:
    """Менеджер датасетов для ML обучения"""
    
    def __init__(self, db: DatabaseManager):
        """
        Инициализация менеджера датасетов
        
        Args:
            db: Менеджер базы данных
        """
        self.db = db
    
    def create_dataset_version(self, name: str, description: str = "",
                             base_version_id: int = None,
                             metadata: Dict = None) -> int:
        """
        Создание новой версии датасета
        
        Args:
            name: Имя версии датасета
            description: Описание
            base_version_id: ID базовой версии (для инкрементальных)
            metadata: Дополнительные метаданные
            
        Returns:
            ID созданной версии
        """
        version_id = self.db.create_dataset_version(
            name, description, base_version_id, metadata
        )
        logger.info(f"Created dataset version {version_id}: {name}")
        return version_id
    
    def prepare_training_dataset(self,
                                version_id: int,
                                filters: Optional[Dict] = None,
                                min_length: int = 1000) -> Dict:
        """
        Подготовка датасета для обучения
        
        Args:
            version_id: ID версии датасета
            filters: Фильтры для отбора документов
            min_length: Минимальная длина контента
            
        Returns:
            Словарь с информацией о созданном датасете
        """
        logger.info(f"Preparing training dataset for version {version_id}")
        
        # Получаем документы согласно фильтрам
        documents = self.db.get_documents_for_training(
            filters=filters,
            min_length=min_length
        )
        
        logger.info(f"Found {len(documents)} documents for training")
        
        # Формируем датасет в формате для обучения
        dataset = {
            'version_id': version_id,
            'samples': [],
            'metadata': {
                'total_documents': len(documents),
                'created_at': datetime.utcnow().isoformat(),
                'filters': filters,
                'min_length': min_length
            }
        }
        
        for doc in documents:
            sample = self._format_for_training(doc)
            dataset['samples'].append(sample)
        
        # Сохраняем датасет
        self.db.save_dataset(version_id, dataset)
        
        size_mb = self._estimate_size(dataset)
        
        logger.info(f"Dataset prepared: {len(dataset['samples'])} samples, "
                   f"{size_mb:.2f} MB")
        
        return {
            'version_id': version_id,
            'total_samples': len(dataset['samples']),
            'size_mb': size_mb
        }
    
    def _format_for_training(self, doc: Dict) -> Dict:
        """
        Форматирование документа для обучения
        
        Args:
            doc: Документ из БД
            
        Returns:
            Форматированный образец для обучения
        """
        text = self._prepare_text(doc)
        
        sample = {
            'id': doc.get('document_id') or doc.get('id'),
            'text': text,
            'metadata': {
                'title': doc.get('title'),
                'type': doc.get('document_type'),
                'number': doc.get('document_number'),
                'date': doc.get('date'),
                'source_url': doc.get('url')
            }
        }
        
        # Вычисляем хеш для дедупликации
        sample['sample_hash'] = self._calculate_sample_hash(sample)
        
        return sample
    
    def _prepare_text(self, doc: Dict) -> str:
        """
        Подготовка текста для обучения
        
        Args:
            doc: Документ из БД
            
        Returns:
            Отформатированный текст
        """
        parts = []
        
        if doc.get('title'):
            parts.append(f"=== {doc['title']} ===")
        
        if doc.get('document_type'):
            parts.append(f"Type: {doc['document_type']}")
        
        if doc.get('document_number'):
            parts.append(f"Number: {doc['document_number']}")
        
        parts.append("")  # Пустая строка
        parts.append(doc.get('content', ''))
        
        return "\n".join(parts)
    
    def _calculate_sample_hash(self, sample: Dict) -> str:
        """Вычисление хеша образца для дедупликации"""
        # Используем только текст для хеширования
        text = sample.get('text', '')
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    def _estimate_size(self, dataset: Dict) -> float:
        """Оценка размера датасета в MB"""
        json_str = json.dumps(dataset, ensure_ascii=False)
        size_bytes = len(json_str.encode('utf-8'))
        return size_bytes / (1024 * 1024)
    
    def get_incremental_updates(self,
                                last_version_id: int,
                                since_date: Optional[datetime] = None) -> List[Dict]:
        """
        Получение инкрементальных обновлений для дообучения
        
        Args:
            last_version_id: ID последней версии датасета
            since_date: Дата, с которой искать изменения (если не указана, берется из версии)
            
        Returns:
            Список новых/измененных образцов
        """
        last_version = self.db.get_dataset_version(last_version_id)
        if not last_version:
            raise ValueError(f"Dataset version {last_version_id} not found")
        
        if since_date is None:
            since_date = last_version['created_at']
        
        # Получаем новые/измененные документы
        new_docs = self.db.get_documents_modified_since(since_date)
        
        logger.info(f"Found {len(new_docs)} modified documents since {since_date}")
        
        # Формируем инкрементальный датасет
        incremental = []
        for doc in new_docs:
            sample = self._format_for_training(doc)
            # Определяем тип изменения
            if doc.get('created_at') and doc['created_at'] > since_date:
                sample['change_type'] = 'new'
            else:
                sample['change_type'] = 'updated'
            incremental.append(sample)
        
        return incremental
    
    def create_incremental_dataset(self,
                                  base_version_id: int,
                                  new_samples: List[Dict]) -> int:
        """
        Создание инкрементального датасета для дообучения
        
        Args:
            base_version_id: ID базовой версии
            new_samples: Новые/измененные образцы
            
        Returns:
            ID созданной версии
        """
        base_version = self.db.get_dataset_version(base_version_id)
        if not base_version:
            raise ValueError(f"Base version {base_version_id} not found")
        
        # Создаем новую версию на основе предыдущей
        new_version_id = self.create_dataset_version(
            name=f"{base_version['name']}_incremental_{datetime.utcnow().strftime('%Y%m%d')}",
            description=f"Incremental update from version {base_version_id}",
            base_version_id=base_version_id
        )
        
        # Сохраняем только новые/измененные образцы
        incremental_dataset = {
            'version_id': new_version_id,
            'base_version_id': base_version_id,
            'samples': new_samples,
            'metadata': {
                'total_samples': len(new_samples),
                'created_at': datetime.utcnow().isoformat(),
                'is_incremental': True
            }
        }
        
        self.db.save_dataset(new_version_id, incremental_dataset)
        
        logger.info(f"Created incremental dataset version {new_version_id} "
                   f"with {len(new_samples)} samples")
        
        return new_version_id
    
    def export_for_training(self, version_id: int, format: str = 'jsonl',
                          output_file: Optional[str] = None) -> str:
        """
        Экспорт датасета в формате для обучения
        
        Args:
            version_id: ID версии датасета
            format: Формат экспорта ('jsonl', 'text', 'huggingface')
            output_file: Путь к файлу для сохранения (если не указан, возвращается строка)
            
        Returns:
            Путь к файлу или содержимое (если output_file не указан)
        """
        # Получаем образцы из БД
        query = """
            SELECT sample_data FROM dataset_samples 
            WHERE version_id = %s
            ORDER BY id
        """
        samples = self.db.execute_query(query, (version_id,))
        
        if format == 'jsonl':
            # JSON Lines формат
            output_lines = []
            for row in samples:
                output_lines.append(json.dumps(row['sample_data'], ensure_ascii=False))
            output = '\n'.join(output_lines)
        
        elif format == 'text':
            # Текстовый формат
            output_lines = []
            for row in samples:
                sample = row['sample_data']
                output_lines.append(sample.get('text', ''))
                output_lines.append("\n" + "="*80 + "\n")
            output = '\n'.join(output_lines)
        
        elif format == 'huggingface':
            # Формат для HuggingFace Datasets
            # Структурированный формат
            data = {
                'text': [],
                'metadata': []
            }
            for row in samples:
                sample = row['sample_data']
                data['text'].append(sample.get('text', ''))
                data['metadata'].append(sample.get('metadata', {}))
            output = json.dumps(data, ensure_ascii=False, indent=2)
        
        else:
            raise ValueError(f"Unknown format: {format}")
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output)
            logger.info(f"Exported dataset version {version_id} to {output_file} ({format})")
            return output_file
        else:
            return output

