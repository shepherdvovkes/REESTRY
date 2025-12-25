"""
Backend API для управления датасетами, промптами и историей LLM обработки
с поддержкой WebSocket для realtime обновлений
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from datetime import datetime
import json
import sqlite3
import os
from typing import Dict, List, Optional
import logging
import threading
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # Разрешаем CORS для frontend

# Инициализация SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Путь к базе данных
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'llm_history.db')

def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Таблица промптов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prompts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            system_prompt TEXT,
            user_prompt_template TEXT,
            algorithm_step TEXT,
            temperature REAL DEFAULT 0.2,
            max_tokens INTEGER DEFAULT -1,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица истории LLM вызовов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS llm_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt_id INTEGER,
            algorithm_step TEXT,
            input_data TEXT,
            output_data TEXT,
            model TEXT,
            temperature REAL,
            tokens_used INTEGER,
            response_time_ms INTEGER,
            success BOOLEAN,
            error_message TEXT,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (prompt_id) REFERENCES prompts(id)
        )
    ''')
    
    # Таблица датасетов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS datasets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            version TEXT,
            total_samples INTEGER DEFAULT 0,
            status TEXT DEFAULT 'draft',
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица связи датасетов с историей обработки
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dataset_processing_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_id INTEGER,
            llm_history_id INTEGER,
            sample_index INTEGER,
            FOREIGN KEY (dataset_id) REFERENCES datasets(id),
            FOREIGN KEY (llm_history_id) REFERENCES llm_history(id)
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("Database initialized")

# Инициализация БД при старте
init_db()

# ========== API для промптов ==========

@app.route('/api/prompts', methods=['GET'])
def get_prompts():
    """Получить все промпты"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM prompts 
        ORDER BY created_at DESC
    ''')
    prompts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(prompts)

@app.route('/api/prompts/<int:prompt_id>', methods=['GET'])
def get_prompt(prompt_id):
    """Получить промпт по ID"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM prompts WHERE id = ?', (prompt_id,))
    prompt = cursor.fetchone()
    conn.close()
    
    if prompt:
        return jsonify(dict(prompt))
    return jsonify({'error': 'Prompt not found'}), 404

@app.route('/api/prompts', methods=['POST'])
def create_prompt():
    """Создать новый промпт"""
    data = request.json
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO prompts 
            (name, description, system_prompt, user_prompt_template, 
             algorithm_step, temperature, max_tokens, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['name'],
            data.get('description', ''),
            data.get('system_prompt', ''),
            data.get('user_prompt_template', ''),
            data.get('algorithm_step', ''),
            data.get('temperature', 0.2),
            data.get('max_tokens', -1),
            data.get('is_active', True)
        ))
        prompt_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Отправляем событие через WebSocket
        socketio.emit('prompt_created', {'id': prompt_id, 'data': data})
        socketio.emit('stats_updated')  # Обновляем статистику
        
        return jsonify({'id': prompt_id, 'message': 'Prompt created'}), 201
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': 'Prompt name already exists'}), 400
    except Exception as e:
        conn.close()
        logger.error(f"Error creating prompt: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/prompts/<int:prompt_id>', methods=['PUT'])
def update_prompt(prompt_id):
    """Обновить промпт"""
    data = request.json
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE prompts 
            SET name = ?, description = ?, system_prompt = ?, 
                user_prompt_template = ?, algorithm_step = ?,
                temperature = ?, max_tokens = ?, is_active = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (
            data['name'],
            data.get('description', ''),
            data.get('system_prompt', ''),
            data.get('user_prompt_template', ''),
            data.get('algorithm_step', ''),
            data.get('temperature', 0.2),
            data.get('max_tokens', -1),
            data.get('is_active', True),
            prompt_id
        ))
        conn.commit()
        conn.close()
        
        # Отправляем событие через WebSocket
        socketio.emit('prompt_updated', {'id': prompt_id, 'data': data})
        
        return jsonify({'message': 'Prompt updated'})
    except Exception as e:
        conn.close()
        logger.error(f"Error updating prompt: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/prompts/<int:prompt_id>', methods=['DELETE'])
def delete_prompt(prompt_id):
    """Удалить промпт"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM prompts WHERE id = ?', (prompt_id,))
    conn.commit()
    conn.close()
    
    # Отправляем событие через WebSocket
    socketio.emit('prompt_deleted', {'id': prompt_id})
    socketio.emit('stats_updated')
    
    return jsonify({'message': 'Prompt deleted'})

# ========== API для истории LLM обработки ==========

@app.route('/api/llm-history', methods=['GET'])
def get_llm_history():
    """Получить историю LLM обработки"""
    limit = request.args.get('limit', 100, type=int)
    algorithm_step = request.args.get('algorithm_step', None)
    prompt_id = request.args.get('prompt_id', None, type=int)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = '''
        SELECT h.*, p.name as prompt_name 
        FROM llm_history h
        LEFT JOIN prompts p ON h.prompt_id = p.id
        WHERE 1=1
    '''
    params = []
    
    if algorithm_step:
        query += ' AND h.algorithm_step = ?'
        params.append(algorithm_step)
    
    if prompt_id:
        query += ' AND h.prompt_id = ?'
        params.append(prompt_id)
    
    query += ' ORDER BY h.created_at DESC LIMIT ?'
    params.append(limit)
    
    cursor.execute(query, params)
    history = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(history)

@app.route('/api/llm-history/<int:history_id>', methods=['GET'])
def get_llm_history_item(history_id):
    """Получить конкретную запись истории"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT h.*, p.name as prompt_name, p.system_prompt, p.user_prompt_template
        FROM llm_history h
        LEFT JOIN prompts p ON h.prompt_id = p.id
        WHERE h.id = ?
    ''', (history_id,))
    item = cursor.fetchone()
    conn.close()
    
    if item:
        return jsonify(dict(item))
    return jsonify({'error': 'History item not found'}), 404

@app.route('/api/llm-history', methods=['POST'])
def log_llm_call():
    """Записать вызов LLM в историю"""
    data = request.json
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO llm_history 
            (prompt_id, algorithm_step, input_data, output_data, 
             model, temperature, tokens_used, response_time_ms, 
             success, error_message, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('prompt_id'),
            data.get('algorithm_step', ''),
            json.dumps(data.get('input_data', {})),
            json.dumps(data.get('output_data', {})),
            data.get('model', ''),
            data.get('temperature', 0.2),
            data.get('tokens_used', 0),
            data.get('response_time_ms', 0),
            data.get('success', True),
            data.get('error_message'),
            json.dumps(data.get('metadata', {}))
        ))
        history_id = cursor.lastrowid
        conn.commit()
        
        # Получаем полную запись для отправки через WebSocket
        cursor.execute('''
            SELECT h.*, p.name as prompt_name 
            FROM llm_history h
            LEFT JOIN prompts p ON h.prompt_id = p.id
            WHERE h.id = ?
        ''', (history_id,))
        item = dict(cursor.fetchone())
        conn.close()
        
        # Отправляем событие через WebSocket для realtime обновления
        socketio.emit('llm_call_logged', item)
        socketio.emit('stats_updated')  # Обновляем статистику
        
        return jsonify({'id': history_id, 'message': 'LLM call logged'}), 201
    except Exception as e:
        conn.close()
        logger.error(f"Error logging LLM call: {e}")
        return jsonify({'error': str(e)}), 500

# ========== API для датасетов ==========

@app.route('/api/datasets', methods=['GET'])
def get_datasets():
    """Получить все датасеты"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT d.*, 
               COUNT(DISTINCT dph.llm_history_id) as processed_samples
        FROM datasets d
        LEFT JOIN dataset_processing_history dph ON d.id = dph.dataset_id
        GROUP BY d.id
        ORDER BY d.created_at DESC
    ''')
    datasets = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(datasets)

@app.route('/api/datasets/<int:dataset_id>', methods=['GET'])
def get_dataset(dataset_id):
    """Получить датасет по ID"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM datasets WHERE id = ?', (dataset_id,))
    dataset = cursor.fetchone()
    conn.close()
    
    if dataset:
        return jsonify(dict(dataset))
    return jsonify({'error': 'Dataset not found'}), 404

@app.route('/api/datasets', methods=['POST'])
def create_dataset():
    """Создать новый датасет"""
    data = request.json
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO datasets 
            (name, description, version, total_samples, status, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            data['name'],
            data.get('description', ''),
            data.get('version', '1.0'),
            data.get('total_samples', 0),
            data.get('status', 'draft'),
            json.dumps(data.get('metadata', {}))
        ))
        dataset_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({'id': dataset_id, 'message': 'Dataset created'}), 201
    except Exception as e:
        conn.close()
        logger.error(f"Error creating dataset: {e}")
        return jsonify({'error': str(e)}), 500

# ========== API для статистики и алгоритма ==========

@app.route('/api/algorithm-steps', methods=['GET'])
def get_algorithm_steps():
    """Получить все шаги алгоритма, где используется LLM"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT DISTINCT algorithm_step, 
               COUNT(*) as call_count,
               COUNT(DISTINCT prompt_id) as prompt_count
        FROM llm_history
        WHERE algorithm_step IS NOT NULL AND algorithm_step != ''
        GROUP BY algorithm_step
        ORDER BY call_count DESC
    ''')
    steps = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(steps)

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Получить общую статистику"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Статистика по промптам
    cursor.execute('SELECT COUNT(*) as count FROM prompts')
    prompts_count = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM prompts WHERE is_active = 1')
    active_prompts = cursor.fetchone()['count']
    
    # Статистика по истории
    cursor.execute('SELECT COUNT(*) as count FROM llm_history')
    total_calls = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM llm_history WHERE success = 1')
    successful_calls = cursor.fetchone()['count']
    
    cursor.execute('SELECT SUM(tokens_used) as total FROM llm_history WHERE tokens_used IS NOT NULL')
    total_tokens = cursor.fetchone()['total'] or 0
    
    cursor.execute('SELECT AVG(response_time_ms) as avg FROM llm_history WHERE response_time_ms IS NOT NULL')
    avg_response_time = cursor.fetchone()['avg'] or 0
    
    # Статистика по датасетам
    cursor.execute('SELECT COUNT(*) as count FROM datasets')
    datasets_count = cursor.fetchone()['count']
    
    conn.close()
    
    return jsonify({
        'prompts': {
            'total': prompts_count,
            'active': active_prompts
        },
        'llm_calls': {
            'total': total_calls,
            'successful': successful_calls,
            'failed': total_calls - successful_calls,
            'total_tokens': total_tokens,
            'avg_response_time_ms': round(avg_response_time, 2)
        },
        'datasets': {
            'total': datasets_count
        }
    })

# ========== WebSocket обработчики ==========

@socketio.on('connect')
def handle_connect():
    """Обработчик подключения клиента"""
    logger.info('Client connected')
    emit('connected', {'message': 'Connected to REESTRY API'})

@socketio.on('disconnect')
def handle_disconnect():
    """Обработчик отключения клиента"""
    logger.info('Client disconnected')

@socketio.on('subscribe_stats')
def handle_subscribe_stats():
    """Подписка на обновления статистики"""
    emit('stats_subscribed', {'message': 'Subscribed to stats updates'})

@socketio.on('subscribe_history')
def handle_subscribe_history():
    """Подписка на обновления истории"""
    emit('history_subscribed', {'message': 'Subscribed to history updates'})

# Функция для периодической отправки статистики (опционально)
def send_periodic_stats():
    """Периодическая отправка статистики (каждые 5 секунд)"""
    while True:
        time.sleep(5)
        try:
            # Получаем актуальную статистику
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) as count FROM prompts')
            prompts_count = cursor.fetchone()['count']
            
            cursor.execute('SELECT COUNT(*) as count FROM prompts WHERE is_active = 1')
            active_prompts = cursor.fetchone()['count']
            
            cursor.execute('SELECT COUNT(*) as count FROM llm_history')
            total_calls = cursor.fetchone()['count']
            
            cursor.execute('SELECT COUNT(*) as count FROM llm_history WHERE success = 1')
            successful_calls = cursor.fetchone()['count']
            
            cursor.execute('SELECT SUM(tokens_used) as total FROM llm_history WHERE tokens_used IS NOT NULL')
            total_tokens = cursor.fetchone()['total'] or 0
            
            cursor.execute('SELECT AVG(response_time_ms) as avg FROM llm_history WHERE response_time_ms IS NOT NULL')
            avg_response_time = cursor.fetchone()['avg'] or 0
            
            cursor.execute('SELECT COUNT(*) as count FROM datasets')
            datasets_count = cursor.fetchone()['count']
            
            conn.close()
            
            stats = {
                'prompts': {
                    'total': prompts_count,
                    'active': active_prompts
                },
                'llm_calls': {
                    'total': total_calls,
                    'successful': successful_calls,
                    'failed': total_calls - successful_calls,
                    'total_tokens': total_tokens,
                    'avg_response_time_ms': round(avg_response_time, 2)
                },
                'datasets': {
                    'total': datasets_count
                }
            }
            
            socketio.emit('stats_update', stats)
        except Exception as e:
            logger.error(f"Error sending periodic stats: {e}")

# Запуск фонового потока для периодической статистики
stats_thread = threading.Thread(target=send_periodic_stats, daemon=True)
stats_thread.start()

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)

