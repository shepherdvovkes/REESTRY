#!/usr/bin/env python3
"""
Скрипт для применения миграций базы данных
"""
import os
import sys
import psycopg2
from pathlib import Path

def apply_migrations(db_config: dict, migrations_dir: str = None):
    """
    Применить все миграции из директории
    
    Args:
        db_config: Конфигурация БД (host, port, database, user, password)
        migrations_dir: Путь к директории с миграциями
    """
    if migrations_dir is None:
        migrations_dir = Path(__file__).parent / 'migrations'
    else:
        migrations_dir = Path(migrations_dir)
    
    # Подключаемся к БД
    conn = psycopg2.connect(**db_config)
    conn.autocommit = False
    
    try:
        cursor = conn.cursor()
        
        # Создаем таблицу для отслеживания примененных миграций
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(255) PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Получаем список уже примененных миграций
        cursor.execute("SELECT version FROM schema_migrations")
        applied = {row[0] for row in cursor.fetchall()}
        
        # Находим все SQL файлы миграций
        migration_files = sorted(migrations_dir.glob('*.sql'))
        
        print(f"Found {len(migration_files)} migration files")
        
        for migration_file in migration_files:
            version = migration_file.stem
            
            if version in applied:
                print(f"⏭️  Skipping {version} (already applied)")
                continue
            
            print(f"📝 Applying {version}...")
            
            try:
                # Читаем и выполняем миграцию
                with open(migration_file, 'r', encoding='utf-8') as f:
                    migration_sql = f.read()
                
                # Выполняем миграцию
                cursor.execute(migration_sql)
                
                # Записываем в таблицу миграций
                cursor.execute(
                    "INSERT INTO schema_migrations (version) VALUES (%s)",
                    (version,)
                )
                
                conn.commit()
                print(f"✅ Applied {version}")
                
            except Exception as e:
                conn.rollback()
                print(f"❌ Error applying {version}: {e}")
                raise
        
        print("\n✅ All migrations applied successfully!")
        
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Apply database migrations')
    parser.add_argument('--host', default='localhost', help='PostgreSQL host')
    parser.add_argument('--port', type=int, default=5432, help='PostgreSQL port')
    parser.add_argument('--database', default='reestry', help='Database name')
    parser.add_argument('--user', default='reestry_user', help='Database user')
    parser.add_argument('--password', default='reestry_password', help='Database password')
    parser.add_argument('--migrations-dir', help='Path to migrations directory')
    
    args = parser.parse_args()
    
    db_config = {
        'host': args.host,
        'port': args.port,
        'database': args.database,
        'user': args.user,
        'password': args.password
    }
    
    # Можно также использовать переменные окружения
    if os.getenv('POSTGRES_HOST'):
        db_config['host'] = os.getenv('POSTGRES_HOST')
    if os.getenv('POSTGRES_PORT'):
        db_config['port'] = int(os.getenv('POSTGRES_PORT'))
    if os.getenv('POSTGRES_DB'):
        db_config['database'] = os.getenv('POSTGRES_DB')
    if os.getenv('POSTGRES_USER'):
        db_config['user'] = os.getenv('POSTGRES_USER')
    if os.getenv('POSTGRES_PASSWORD'):
        db_config['password'] = os.getenv('POSTGRES_PASSWORD')
    
    apply_migrations(db_config, args.migrations_dir)

