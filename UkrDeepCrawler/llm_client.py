"""
Клиент для работы с LMStudio API
"""
import requests
import json
from typing import Dict, List, Optional
import time

class LLMClient:
    """Клиент для взаимодействия с LMStudio API"""
    
    def __init__(self, url: str, model: str = "openai/gpt-oss-20b", timeout: int = 60):
        self.url = url
        self.model = model
        self.timeout = timeout
        self.request_count = 0
    
    def call(self, user_prompt: str, system_prompt: Optional[str] = None, 
             temperature: float = 0.2, max_retries: int = 3) -> str:
        """
        Вызов LMStudio API
        
        Args:
            user_prompt: Пользовательский промпт
            system_prompt: Системный промпт (опционально)
            temperature: Температура для генерации (0.2 = более детерминировано)
            max_retries: Максимальное количество попыток при ошибке
        
        Returns:
            Ответ от LLM
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": user_prompt})
        
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
                
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0]["message"]["content"]
                else:
                    raise ValueError("Invalid response format from LMStudio")
                    
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Экспоненциальная задержка
                    print(f"⚠️  LLM request failed (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"❌ LLM request failed after {max_retries} attempts: {e}")
                    return "{}"
            except (KeyError, ValueError) as e:
                print(f"❌ Error parsing LLM response: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                else:
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

