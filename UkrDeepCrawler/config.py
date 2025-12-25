"""
Конфигурация для UkrDeepCrawler
"""

# LMStudio server URL
LMSTUDIO_URL = "http://192.168.0.60:1234/v1/chat/completions"
LMSTUDIO_MODEL = "openai/gpt-oss-20b"

# Домены для фильтрации (украинский госсектор)
ALLOWED_DOMAINS = [
    '.gov.ua',
    '.minjust.gov.ua',
    '.data.gov.ua',
    '.nazk.gov.ua',
    '.rnbo.gov.ua',
    '.opendatabot.ua',
    '.tax.gov.ua',
    '.land.gov.ua',
    '.court.gov.ua'
]

# Параметры обхода
MAX_DEPTH = 5
MAX_PAGES = 1000
REQUEST_DELAY = 1.0  # секунды между запросами
LLM_TIMEOUT = 60  # секунды для LLM запросов

# User-Agent
USER_AGENT = 'Mozilla/5.0 (compatible; UkrDeepCrawler/1.0; +https://github.com/your-repo)'

