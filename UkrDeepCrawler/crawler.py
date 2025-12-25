#!/usr/bin/env python3
"""
Deep Crawler с LLM для поиска источников открытых данных в украинском сегменте интернета
"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs
from dataclasses import dataclass
from typing import Set, List, Dict, Optional, Tuple
import time
import json
from playwright.sync_api import sync_playwright
from queue import PriorityQueue
import threading

from llm_client import LLMClient
import config


@dataclass
class CrawlTask:
    """Задача для обхода URL"""
    url: str
    priority: int  # 1 = highest, 10 = lowest
    depth: int
    source_type: str = "unknown"  # registry, api, data_portal, etc.
    
    def __lt__(self, other):
        """Для PriorityQueue - меньший priority = выше в очереди"""
        return self.priority < other.priority


class LLMCrawler:
    """Интеллектуальный crawler с использованием LLM для анализа контента"""
    
    def __init__(self, lmstudio_url: Optional[str] = None, model: Optional[str] = None):
        """
        Инициализация crawler
        
        Args:
            lmstudio_url: URL LMStudio server (по умолчанию из config)
            model: Название модели (по умолчанию из config)
        """
        self.lmstudio_url = lmstudio_url or config.LMSTUDIO_URL
        self.model = model or config.LMSTUDIO_MODEL
        
        # LLM клиент с логированием
        self.llm = LLMClient(
            self.lmstudio_url, 
            self.model, 
            timeout=config.LLM_TIMEOUT,
            enable_logging=True,
            algorithm_step="crawler"
        )
        
        # URL management
        self.visited_urls: Set[str] = set()
        self.url_queue = PriorityQueue()  # (priority, task)
        self.relevant_urls: List[Dict] = []  # Найденные релевантные URL
        
        # Statistics
        self.stats = {
            'total_crawled': 0,
            'relevant_found': 0,
            'api_endpoints': 0,
            'registries': 0,
            'data_files': 0,
            'rss_feeds': 0,
            'errors': 0
        }
        
        # Domain filters для украинского сегмента
        self.allowed_domains = config.ALLOWED_DOMAINS
        
        # Playwright для JS-страниц
        self.playwright = None
        self.browser = None
        self.playwright_lock = threading.Lock()
        
        # Rate limiting
        self.last_request_time = 0
        self.request_delay = config.REQUEST_DELAY
    
    def start_playwright(self):
        """Инициализация Playwright для JS-рендеринга"""
        with self.playwright_lock:
            if not self.playwright:
                self.playwright = sync_playwright().start()
                self.browser = self.playwright.chromium.launch(headless=True)
    
    def stop_playwright(self):
        """Остановка Playwright"""
        with self.playwright_lock:
            if self.browser:
                self.browser.close()
                self.browser = None
            if self.playwright:
                self.playwright.stop()
                self.playwright = None
    
    def is_relevant_domain(self, url: str) -> bool:
        """Проверка, что URL в украинском госсегменте"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            return any(allowed in domain for allowed in self.allowed_domains)
        except:
            return False
    
    def normalize_url(self, url: str) -> str:
        """Нормализация URL (удаление якорей, параметров сортировки)"""
        try:
            parsed = urlparse(url)
            # Убираем якоря, но сохраняем важные параметры
            normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if parsed.query:
                # Сохраняем только важные параметры (id, page и т.д.)
                params = parse_qs(parsed.query)
                important_params = ['id', 'page', 'doc_id', 'api_key', 'search']
                filtered_params = {k: v[0] for k, v in params.items() 
                                 if k in important_params}
                if filtered_params:
                    query = '&'.join(f"{k}={v}" for k, v in filtered_params.items())
                    normalized += f"?{query}"
            return normalized
        except:
            return url
    
    def rate_limit(self):
        """Rate limiting между запросами"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.request_delay:
            time.sleep(self.request_delay - time_since_last)
        self.last_request_time = time.time()
    
    def fetch_page(self, url: str, use_js: bool = False) -> Tuple[Optional[str], bool]:
        """Загрузка страницы (HTTP или через Playwright)"""
        self.rate_limit()
        
        try:
            if use_js:
                if not self.browser:
                    self.start_playwright()
                
                with self.playwright_lock:
                    page = self.browser.new_page()
                    try:
                        page.goto(url, wait_until='networkidle', timeout=30000)
                        time.sleep(2)  # Дать время на загрузку JS
                        content = page.content()
                        return content, True
                    finally:
                        page.close()
            else:
                response = requests.get(
                    url,
                    headers={
                        'User-Agent': config.USER_AGENT,
                        'Accept': 'text/html,application/xhtml+xml'
                    },
                    timeout=30,
                    allow_redirects=True
                )
                response.raise_for_status()
                return response.text, True
        except Exception as e:
            print(f"   ⚠️  Error fetching {url}: {e}")
            self.stats['errors'] += 1
            return None, False
    
    def llm_analyze_page(self, html_content: str, url: str) -> Dict:
        """LLM анализирует страницу на релевантность"""
        # Извлекаем текст для анализа (первые 5000 символов)
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Удаляем скрипты и стили
        for script in soup(["script", "style", "nav", "header", "footer"]):
            script.decompose()
        
        text_content = soup.get_text()[:5000]
        title = soup.find('title')
        title_text = title.get_text() if title else ""
        
        # Извлекаем все ссылки для контекста
        links = soup.find_all('a', href=True)
        link_texts = [f"{link.get_text(strip=True)} -> {link.get('href')}" 
                      for link in links[:20]]
        
        system_prompt = """Ты эксперт по анализу украинских государственных порталов и реестров.
Твоя задача - находить источники открытых данных, API endpoints и реестры.
Всегда отвечай валидным JSON без дополнительных комментариев."""
        
        user_prompt = f"""Проанализируй эту страницу украинского государственного портала и определи:

URL: {url}
Заголовок: {title_text}
Текст страницы (первые 5000 символов):
{text_content}

Ссылки на странице:
{chr(10).join(link_texts)}

Определи:
1. Тип страницы (data_portal, registry, api_docs, search_page, обычная_страница)
2. Релевантность для поиска источников данных (1-10, где 10 = очень релевантно)
3. Приоритет обхода ссылок на этой странице (1-10, где 1 = высокий)
4. Ключевые слова, указывающие на наличие данных (реестр, API, завантажити, дані, etc.)

Верни JSON:
{{
    "page_type": "...",
    "relevance": число,
    "crawl_priority": число,
    "keywords_found": ["...", "..."],
    "is_data_source": true/false,
    "reasoning": "краткое объяснение"
}}"""

        response = self.llm.call(
            user_prompt, 
            system_prompt, 
            temperature=0.2,
            algorithm_step="llm_analyze_page"
        )
        result = self.llm.parse_json_response(response)
        
        if result:
            return result
        else:
            # Fallback если LLM не вернул JSON
            return {
                "page_type": "unknown",
                "relevance": 5,
                "crawl_priority": 5,
                "keywords_found": [],
                "is_data_source": False,
                "reasoning": "LLM parsing error"
            }
    
    def llm_extract_relevant_links(self, html_content: str, page_analysis: Dict) -> List[Dict]:
        """LLM извлекает релевантные ссылки из страницы"""
        soup = BeautifulSoup(html_content, 'html.parser')
        all_links = soup.find_all('a', href=True)
        
        # Подготовка контекста для LLM
        links_context = []
        for link in all_links[:50]:  # Первые 50 ссылок
            href = link.get('href', '')
            text = link.get_text(strip=True)
            links_context.append(f"Текст: '{text}' -> URL: {href}")
        
        system_prompt = """Ты эксперт по поиску источников данных в украинских государственных порталах.
Найди релевантные ссылки на реестры, API и файлы данных.
Всегда отвечай валидным JSON массивом."""
        
        user_prompt = f"""Из этого списка ссылок найди релевантные для поиска источников данных:

Контекст страницы:
- Тип: {page_analysis.get('page_type')}
- Релевантность: {page_analysis.get('relevance')}/10

Ссылки:
{chr(10).join(links_context)}

Найди ссылки на:
1. Реестры (реестр, register, registry)
2. API endpoints (/api/, /rest/, /graphql)
3. Портал данных (data, відкриті дані, open data)
4. Файлы данных (.csv, .json, .xml, завантажити)
5. Документацию API
6. Страницы поиска в реестрах
7. RSS/Atom feeds (/feed, /rss, /atom, .rss, .xml с RSS-структурой, ссылки с текстом "RSS", "Feed", "Подписка")
8. Источники обновлений данных (новости, изменения, обновления)

Для каждой релевантной ссылки определи:
- Приоритет (1-10, где 1 = очень важно, RSS-фиды должны иметь приоритет 2-3)
- Тип источника (registry, api, data_file, documentation, rss)
- Уверенность (1-10)

Верни JSON массив:
[
    {{
        "url": "полный URL",
        "text": "текст ссылки",
        "priority": число,
        "source_type": "registry/api/data_file/etc",
        "confidence": число,
        "reasoning": "почему релевантно"
    }},
    ...
]

Если релевантных ссылок нет, верни пустой массив []."""

        response = self.llm.call(
            user_prompt, 
            system_prompt, 
            temperature=0.2,
            algorithm_step="llm_extract_relevant_links"
        )
        result = self.llm.parse_json_response(response)
        
        if isinstance(result, list):
            return result
        elif isinstance(result, dict) and 'links' in result:
            return result['links']
        else:
            return []
    
    def extract_all_links(self, html_content: str, base_url: str) -> List[str]:
        """Базовое извлечение всех ссылок (fallback)"""
        soup = BeautifulSoup(html_content, 'html.parser')
        links = []
        
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            try:
                absolute_url = urljoin(base_url, href)
                
                # Фильтруем по доменам
                if self.is_relevant_domain(absolute_url):
                    normalized = self.normalize_url(absolute_url)
                    links.append(normalized)
            except:
                continue
        
        return links
    
    def crawl(self, seed_urls: List[str], max_depth: int = None, max_pages: int = None):
        """
        Основной метод обхода
        
        Args:
            seed_urls: Начальные URL для обхода
            max_depth: Максимальная глубина обхода (по умолчанию из config)
            max_pages: Максимальное количество страниц (по умолчанию из config)
        """
        max_depth = max_depth or config.MAX_DEPTH
        max_pages = max_pages or config.MAX_PAGES
        
        print(f"🚀 Starting crawl with {len(seed_urls)} seed URLs")
        print(f"   Max depth: {max_depth}, Max pages: {max_pages}")
        print(f"   LMStudio: {self.lmstudio_url}")
        print("="*60)
        
        # Добавляем seed URLs в очередь с высоким приоритетом
        for url in seed_urls:
            if self.is_relevant_domain(url):
                task = CrawlTask(
                    url=self.normalize_url(url),
                    priority=1,
                    depth=0,
                    source_type="seed"
                )
                self.url_queue.put((task.priority, task))
        
        self.start_playwright()
        
        try:
            while not self.url_queue.empty() and self.stats['total_crawled'] < max_pages:
                # Извлекаем задачу из очереди
                priority, task = self.url_queue.get()
                url = task.url
                
                # Проверка на уже посещённые
                if url in self.visited_urls:
                    continue
                
                # Проверка глубины
                if task.depth > max_depth:
                    continue
                
                self.visited_urls.add(url)
                self.stats['total_crawled'] += 1
                
                print(f"\n[{self.stats['total_crawled']}/{max_pages}] Crawling: {url}")
                print(f"   Depth: {task.depth}, Priority: {priority}, Type: {task.source_type}")
                
                # Загрузка страницы
                # Определяем, нужен ли JS (эвристика)
                needs_js = any(keyword in url.lower() 
                              for keyword in ['search', 'query', 'filter', 'dynamic', 'ajax'])
                
                html_content, success = self.fetch_page(url, use_js=needs_js)
                
                if not success or not html_content:
                    continue
                
                # LLM анализ страницы
                print(f"   🤖 LLM analyzing page...")
                page_analysis = self.llm_analyze_page(html_content, url)
                
                print(f"   📊 Type: {page_analysis.get('page_type')}, "
                      f"Relevance: {page_analysis.get('relevance')}/10")
                
                # Если страница релевантна - сохраняем
                if page_analysis.get('is_data_source') or page_analysis.get('relevance', 0) >= 7:
                    self.relevant_urls.append({
                        'url': url,
                        'type': page_analysis.get('page_type'),
                        'relevance': page_analysis.get('relevance'),
                        'analysis': page_analysis,
                        'depth': task.depth
                    })
                    self.stats['relevant_found'] += 1
                    print(f"   ✅ Relevant source found!")
                
                # Извлечение RSS-ссылок (всегда, независимо от релевантности)
                print(f"   📡 Searching for RSS feeds...")
                rss_links = self.extract_rss_links(html_content, url)
                for rss_info in rss_links:
                    rss_url = rss_info.get('url')
                    if rss_url and rss_url not in self.visited_urls and self.is_relevant_domain(rss_url):
                        priority = rss_info.get('priority', 3)
                        self.stats['rss_feeds'] += 1
                        
                        new_task = CrawlTask(
                            url=rss_url,
                            priority=priority,
                            depth=task.depth + 1,
                            source_type='rss'
                        )
                        self.url_queue.put((priority, new_task))
                        print(f"      📡 Found RSS feed: {rss_url} (priority {priority})")
                
                # Извлечение ссылок
                if page_analysis.get('relevance', 0) >= 5:
                    # Используем LLM для умного извлечения
                    print(f"   🔍 LLM extracting relevant links...")
                    relevant_links = self.llm_extract_relevant_links(html_content, page_analysis)
                    
                    for link_info in relevant_links:
                        link_url = link_info.get('url')
                        if not link_url:
                            continue
                        
                        # Нормализуем URL
                        try:
                            normalized = self.normalize_url(urljoin(url, link_url))
                        except:
                            continue
                        
                        if normalized not in self.visited_urls and self.is_relevant_domain(normalized):
                            # Определяем приоритет на основе LLM анализа
                            priority = link_info.get('priority', 5)
                            source_type = link_info.get('source_type', 'unknown')
                            
                            # Обновляем статистику
                            if source_type == 'api':
                                self.stats['api_endpoints'] += 1
                            elif source_type == 'registry':
                                self.stats['registries'] += 1
                            elif source_type == 'data_file':
                                self.stats['data_files'] += 1
                            elif source_type == 'rss':
                                self.stats['rss_feeds'] += 1
                            
                            # Добавляем в очередь
                            new_task = CrawlTask(
                                url=normalized,
                                priority=priority,
                                depth=task.depth + 1,
                                source_type=source_type
                            )
                            self.url_queue.put((priority, new_task))
                            
                            print(f"      ✅ Found: {source_type} (priority {priority})")
                else:
                    # Базовое извлечение ссылок для менее релевантных страниц
                    all_links = self.extract_all_links(html_content, url)
                    for link_url in all_links[:10]:  # Ограничиваем для обычных страниц
                        if link_url not in self.visited_urls:
                            task = CrawlTask(
                                url=link_url,
                                priority=7,  # Низкий приоритет
                                depth=task.depth + 1
                            )
                            self.url_queue.put((7, task))
                
                # Периодический вывод статистики
                if self.stats['total_crawled'] % 10 == 0:
                    self.print_stats()
        
        finally:
            self.stop_playwright()
            self.print_final_stats()
    
    def print_stats(self):
        """Вывод текущей статистики"""
        print("\n" + "="*60)
        print("📊 CRAWL STATISTICS")
        print("="*60)
        print(f"   Total crawled: {self.stats['total_crawled']}")
        print(f"   Relevant found: {self.stats['relevant_found']}")
        print(f"   API endpoints: {self.stats['api_endpoints']}")
        print(f"   Registries: {self.stats['registries']}")
        print(f"   Data files: {self.stats['data_files']}")
        print(f"   RSS feeds: {self.stats['rss_feeds']}")
        print(f"   Errors: {self.stats['errors']}")
        print(f"   Queue size: {self.url_queue.qsize()}")
        print(f"   Visited: {len(self.visited_urls)}")
        print(f"   LLM requests: {self.llm.get_stats()['request_count']}")
        print("="*60)
    
    def print_final_stats(self):
        """Финальная статистика"""
        print("\n" + "="*60)
        print("✅ CRAWL COMPLETE")
        print("="*60)
        self.print_stats()
        print(f"\n📋 Found {len(self.relevant_urls)} relevant URLs")
        print("="*60)
    
    def save_results(self, filename: str = "crawl_results.json"):
        """Сохранение результатов"""
        results = {
            'stats': self.stats,
            'llm_stats': self.llm.get_stats(),
            'relevant_urls': self.relevant_urls,
            'total_visited': len(self.visited_urls),
            'timestamp': time.time()
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Results saved to {filename}")


if __name__ == "__main__":
    crawler = LLMCrawler()
    
    seed_urls = [
        "https://data.gov.ua",
        "https://usr.minjust.gov.ua",
        "https://opendatabot.ua",
        "https://nazk.gov.ua",
        "https://minjust.gov.ua/m/edini-ta-derjavni-reestri"
    ]
    
    crawler.crawl(
        seed_urls=seed_urls,
        max_depth=4,
        max_pages=500
    )
    
    crawler.save_results("ukrainian_registries_crawl.json")

