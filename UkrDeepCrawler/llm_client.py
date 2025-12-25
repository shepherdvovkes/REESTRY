"""
Клиент для работы с LMStudio API
"""
import requests
import json
from typing import Dict, List, Optional
import time

# Импорт логгера (опционально, если доступен)
try:
    from llm_logger import LLMLogger
    LOGGING_ENABLED = True
except ImportError:
    LOGGING_ENABLED = False

class LLMClient:
    """Клиент для взаимодействия с LMStudio API"""
    
    def __init__(self, url: str, model: str = "openai/gpt-oss-20b", timeout: int = 60, 
                 enable_logging: bool = True, algorithm_step: str = None):
        """
        Инициализация клиента
        
        Args:
            url: URL LMStudio API
            model: Название модели
            timeout: Таймаут запроса
            enable_logging: Включить логирование вызовов
            algorithm_step: Шаг алгоритма, где используется этот клиент
        """
        self.url = url
        self.model = model
        self.timeout = timeout
        self.request_count = 0
        self.algorithm_step = algorithm_step or "unknown"
        self.enable_logging = enable_logging and LOGGING_ENABLED
        
        if self.enable_logging:
            self.logger = LLMLogger()
    
    def call(self, user_prompt: str, system_prompt: Optional[str] = None, 
             temperature: float = 0.2, max_retries: int = 3,
             algorithm_step: Optional[str] = None) -> str:
        """
        Вызов LMStudio API
        
        Args:
            user_prompt: Пользовательский промпт
            system_prompt: Системный промпт (опционально)
            temperature: Температура для генерации (0.2 = более детерминировано)
            max_retries: Максимальное количество попыток при ошибке
            algorithm_step: Шаг алгоритма (переопределяет self.algorithm_step)
        
        Returns:
            Ответ от LLM
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": user_prompt})
        
        # Определяем шаг алгоритма
        step = algorithm_step or self.algorithm_step
        
        # Подготовка данных для логирования
        start_time = time.time()
        input_data = {
            "user_prompt": user_prompt,
            "system_prompt": system_prompt,
            "messages": messages
        }
        output_data = {}
        error_message = None
        tokens_used = None
        success = False
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.url,
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": -1,
                        "stream": False
                    },
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                result = response.json()
                self.request_count += 1
                
                # Извлекаем информацию о токенах, если доступна
                if "usage" in result:
                    tokens_used = result["usage"].get("total_tokens")
                
                if "choices" in result and len(result["choices"]) > 0:
                    response_text = result["choices"][0]["message"]["content"]
                    output_data = {
                        "response": response_text,
                        "full_response": result
                    }
                    success = True
                    
                    # Логируем успешный вызов
                    if self.enable_logging:
                        response_time_ms = int((time.time() - start_time) * 1000)
                        self.logger.log_llm_call(
                            algorithm_step=step,
                            input_data=input_data,
                            output_data=output_data,
                            model=self.model,
                            temperature=temperature,
                            response_time_ms=response_time_ms,
                            success=True,
                            tokens_used=tokens_used,
                            metadata={"attempt": attempt + 1, "max_retries": max_retries}
                        )
                    
                    return response_text
                else:
                    raise ValueError("Invalid response format from LMStudio")
                    
            except requests.exceptions.RequestException as e:
                error_message = str(e)
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Экспоненциальная задержка
                    print(f"⚠️  LLM request failed (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"❌ LLM request failed after {max_retries} attempts: {e}")
                    # Логируем ошибку
                    if self.enable_logging:
                        response_time_ms = int((time.time() - start_time) * 1000)
                        self.logger.log_llm_call(
                            algorithm_step=step,
                            input_data=input_data,
                            output_data={},
                            model=self.model,
                            temperature=temperature,
                            response_time_ms=response_time_ms,
                            success=False,
                            error_message=error_message,
                            metadata={"attempt": attempt + 1, "max_retries": max_retries}
                        )
                    return "{}"
            except (KeyError, ValueError) as e:
                error_message = str(e)
                print(f"❌ Error parsing LLM response: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                else:
                    # Логируем ошибку парсинга
                    if self.enable_logging:
                        response_time_ms = int((time.time() - start_time) * 1000)
                        self.logger.log_llm_call(
                            algorithm_step=step,
                            input_data=input_data,
                            output_data={},
                            model=self.model,
                            temperature=temperature,
                            response_time_ms=response_time_ms,
                            success=False,
                            error_message=error_message,
                            metadata={"attempt": attempt + 1, "max_retries": max_retries}
                        )
                    return "{}"
        
        return "{}"
    
    def parse_json_response(self, response: str) -> Optional[Dict]:
        """Парсинг JSON ответа от LLM"""
        try:
            # Пытаемся найти JSON в ответе (может быть обёрнут в markdown)
            response = response.strip()
            
            # Убираем markdown code blocks если есть
            if response.startswith("```"):
                lines = response.split("\n")
                # Убираем первую и последнюю строки с ```
                response = "\n".join(lines[1:-1])
            
            return json.loads(response)
        except json.JSONDecodeError:
            # Пытаемся извлечь JSON из текста
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except:
                    pass
            return None
    
    def get_stats(self) -> Dict:
        """Получить статистику использования"""
        return {
            "request_count": self.request_count,
            "url": self.url,
            "model": self.model
        }

