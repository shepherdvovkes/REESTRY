#!/usr/bin/env python3
"""
Application to download all popular documents from zakon.rada.gov.ua
and store them in a database.

Rate Limiting Rules (from zakon.rada.gov.ua):
- Limit on number of pages per minute from single IP
- Excessive requests = temporary denial (several minutes)
- Repeated violations = 24 hour or permanent suspension
- Peak hours: 10:00-13:00 and 14:00-17:00 (may timeout after 10s)
"""
import sqlite3
import requests
from bs4 import BeautifulSoup
import time
import json
import re
from urllib.parse import urljoin, urlparse, parse_qs
from datetime import datetime
import sys
from pathlib import Path
import threading
from queue import Queue
from collections import deque
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class RateLimiter:
    """Rate limiter to track requests per minute"""
    def __init__(self, max_requests_per_minute=30):
        self.max_requests = max_requests_per_minute
        self.request_times = deque()
        self.lock = threading.Lock()
    
    def wait_if_needed(self):
        """Wait if we've exceeded the rate limit"""
        with self.lock:
            now = time.time()
            # Remove requests older than 1 minute
            while self.request_times and self.request_times[0] < now - 60:
                self.request_times.popleft()
            
            # If we're at the limit, wait
            if len(self.request_times) >= self.max_requests:
                sleep_time = 60 - (now - self.request_times[0]) + 0.1
                if sleep_time > 0:
                    return sleep_time
            return 0
    
    def record_request(self):
        """Record that we made a request"""
        with self.lock:
            self.request_times.append(time.time())
    
    def get_current_rate(self):
        """Get current requests per minute"""
        with self.lock:
            now = time.time()
            while self.request_times and self.request_times[0] < now - 60:
                self.request_times.popleft()
            return len(self.request_times)

class DocumentDownloader:
    def __init__(self, db_path='documents.db', max_workers=3, requests_per_minute=30, verbose=False):
        self.db_path = db_path
        self.base_url = 'https://zakon.rada.gov.ua'
        self.max_workers = max_workers
        self.verbose = verbose
        self.rate_limiter = RateLimiter(max_requests_per_minute=requests_per_minute)
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'successful_downloads': 0,
            'skipped': 0,
            'errors': 0,
            'rate_limit_hits': 0,
            'start_time': time.time()
        }
        self.stats_lock = threading.Lock()
        self.db_lock = threading.Lock()  # SQLite needs thread-safe access
        
        # Setup logging
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)
        
        # Create session with retry strategy
        self.session = self._create_session()
        self.init_database()
        
        # Calculate and display optimal parameters
        self._calculate_and_display_parameters()
    
    def _create_session(self):
        """Create a session with retry strategy and connection pooling"""
        session = requests.Session()
        
        # Retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"]
        )
        
        # HTTP adapter with connection pooling
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=self.max_workers,
            pool_maxsize=self.max_workers * 2
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7',
        })
        
        return session
    
    def _calculate_and_display_parameters(self):
        """Calculate and display optimal parameters based on restrictions"""
        self.logger.info("=" * 80)
        self.logger.info("RATE LIMITING CONFIGURATION")
        self.logger.info("=" * 80)
        self.logger.info(f"📊 Website Restrictions (zakon.rada.gov.ua):")
        self.logger.info(f"   • Limit on pages per minute from single IP")
        self.logger.info(f"   • Excessive requests = temporary denial (several minutes)")
        self.logger.info(f"   • Repeated violations = 24h or permanent suspension")
        self.logger.info(f"   • Peak hours (10:00-13:00, 14:00-17:00) may timeout after 10s")
        self.logger.info("")
        self.logger.info(f"⚙️  Current Configuration:")
        self.logger.info(f"   • Max concurrent workers: {self.max_workers}")
        self.logger.info(f"   • Requests per minute limit: {self.rate_limiter.max_requests}")
        self.logger.info(f"   • Requests per second: ~{self.rate_limiter.max_requests / 60:.2f}")
        self.logger.info("")
        
        # Calculate estimated time
        total_docs = 262483
        docs_per_minute = self.rate_limiter.max_requests
        estimated_minutes = total_docs / docs_per_minute
        estimated_hours = estimated_minutes / 60
        estimated_days = estimated_hours / 24
        
        self.logger.info(f"📈 Estimated Performance:")
        self.logger.info(f"   • Documents per minute: {docs_per_minute}")
        self.logger.info(f"   • Estimated time for 262,483 documents:")
        self.logger.info(f"     - {estimated_minutes:.0f} minutes")
        self.logger.info(f"     - {estimated_hours:.1f} hours")
        self.logger.info(f"     - {estimated_days:.2f} days")
        self.logger.info("")
        
        # Calculate optimal settings
        self.logger.info(f"💡 Recommendations:")
        if self.max_workers > 5:
            self.logger.warning(f"   ⚠️  High concurrency ({self.max_workers}) may trigger rate limits")
            self.logger.info(f"   → Consider reducing to 3-5 workers")
        if self.rate_limiter.max_requests > 40:
            self.logger.warning(f"   ⚠️  High request rate ({self.rate_limiter.max_requests}/min) may cause bans")
            self.logger.info(f"   → Consider reducing to 20-30 requests/minute")
        
        # Check if peak hours
        current_hour = datetime.now().hour
        if 10 <= current_hour < 13 or 14 <= current_hour < 17:
            self.logger.warning(f"   ⚠️  Currently in PEAK HOURS ({current_hour}:00)")
            self.logger.info(f"   → Expect slower performance and possible timeouts")
        
        self.logger.info("=" * 80)
        self.logger.info("")
    
    def init_database(self):
        """Initialize SQLite database with documents table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT UNIQUE,
                title TEXT,
                document_type TEXT,
                document_number TEXT,
                date TEXT,
                status TEXT,
                url TEXT,
                content TEXT,
                metadata TEXT,
                downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_document_id ON documents(document_id)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_document_number ON documents(document_number)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_date ON documents(date)
        ''')
        
        conn.commit()
        conn.close()
        self.logger.info(f"✅ Database initialized: {self.db_path}")
    
    def get_document_count(self):
        """Get total number of documents already downloaded"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM documents')
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def extract_document_id(self, url):
        """Extract document ID from URL"""
        # URLs like: https://zakon.rada.gov.ua/laws/show/2341-14
        match = re.search(r'/laws/show/([^/]+)', url)
        if match:
            return match.group(1)
        return None
    
    def _make_request(self, url, description="request"):
        """Make a rate-limited HTTP request"""
        # Wait if we're at the rate limit
        sleep_time = self.rate_limiter.wait_if_needed()
        if sleep_time > 0:
            self.stats['rate_limit_hits'] += 1
            if self.verbose:
                self.logger.debug(f"⏳ Rate limit: waiting {sleep_time:.1f}s")
            time.sleep(sleep_time)
        
        self.rate_limiter.record_request()
        self.stats['total_requests'] += 1
        
        current_rate = self.rate_limiter.get_current_rate()
        if self.verbose:
            self.logger.debug(f"🌐 {description} (Rate: {current_rate}/{self.rate_limiter.max_requests}/min)")
        
        try:
            response = self.session.get(url, timeout=30)
            return response
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Request failed for {url}: {e}")
            raise
    
    def fetch_popular_documents_page(self, page=1, per_page=50):
        """
        Fetch a page of popular documents from the website
        Based on the actual website structure at zakon.rada.gov.ua
        """
        # The website likely uses AJAX/API calls for pagination
        # Try to find the actual API endpoint or use search functionality
        
        # Method 1: Try direct popular documents page (correct URL is /laws/main/d)
        # Pagination format: /laws/main/d/page2, /laws/main/d/page3, etc.
        if page == 1:
            endpoints = [
                f'{self.base_url}/laws/main/d',  # First page (no page number)
            ]
        else:
            endpoints = [
                f'{self.base_url}/laws/main/d/page{page}',  # Correct pagination format
                f'{self.base_url}/laws/main/d?page={page}',  # Alternative format
            ]
        
        for endpoint in endpoints:
            try:
                response = self._make_request(endpoint, f"Fetching page {page}")
                if response.status_code == 200:
                    return response.text
                elif response.status_code == 429:
                    self.logger.warning(f"⚠️  Rate limit hit (429) for page {page}, waiting...")
                    time.sleep(60)
                else:
                    if self.verbose:
                        self.logger.debug(f"Status {response.status_code} for {endpoint}")
            except Exception as e:
                if self.verbose:
                    self.logger.debug(f"Error fetching {endpoint}: {e}")
                continue
        
        # Method 2: Use search API if available
        # Many sites use search endpoints that return JSON
        search_endpoints = [
            f'{self.base_url}/laws/main/search?q=*&page={page}',
            f'{self.base_url}/api/documents?page={page}',
        ]
        
        for endpoint in search_endpoints:
            try:
                response = self.session.get(endpoint, timeout=30)
                if response.status_code == 200:
                    # Check if it's JSON
                    try:
                        data = response.json()
                        if 'documents' in data or 'items' in data:
                            return response.text
                    except:
                        pass
                    return response.text
            except:
                continue
        
        # Method 3: Fallback to main page
        try:
            response = self._make_request(f'{self.base_url}/laws/main', "Fetching main page")
            if response.status_code == 200:
                return response.text
        except Exception as e:
            self.logger.debug(f"Error fetching main page: {e}")
        
        return None
    
    def parse_document_list(self, html):
        """Parse HTML to extract document links and metadata"""
        if not html or len(html) < 100:
            if self.verbose:
                self.logger.debug("HTML too short or empty")
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        documents = []
        seen_ids = set()
        
        # Try to parse as JSON first (if it's an API response)
        try:
            import json
            data = json.loads(html)
            if isinstance(data, dict):
                items = data.get('documents', data.get('items', data.get('data', [])))
                for item in items:
                    if isinstance(item, dict):
                        url = item.get('url') or item.get('link')
                        if url and '/laws/show/' in str(url):
                            full_url = urljoin(self.base_url, url)
                            doc_id = self.extract_document_id(full_url)
                            if doc_id and doc_id not in seen_ids:
                                seen_ids.add(doc_id)
                                documents.append({
                                    'document_id': doc_id,
                                    'title': item.get('title', item.get('name', '')),
                                    'url': full_url,
                                    'document_number': item.get('number'),
                                    'date': item.get('date'),
                                    'document_type': item.get('type')
                                })
                if documents:
                    if self.verbose:
                        self.logger.debug(f"Found {len(documents)} documents via JSON parsing")
                    return documents
        except:
            pass
        
        # Method 1: Find all links to /laws/show/ in href attributes
        links = soup.find_all('a', href=re.compile(r'/laws/show/'))
        
        if self.verbose and len(links) > 0:
            self.logger.debug(f"Found {len(links)} links with /laws/show/ in href")
        
        # Method 2: Search in all href attributes
        if len(links) == 0:
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link.get('href', '')
                if '/laws/show/' in href:
                    links.append(link)
        
        # Method 3: Search in text content for document URLs
        if len(links) == 0:
            text_content = soup.get_text()
            url_pattern = re.compile(r'https?://[^\s]+/laws/show/[^\s\)\"\']+')
            found_urls = url_pattern.findall(text_content)
            if self.verbose and found_urls:
                self.logger.debug(f"Found {len(found_urls)} document URLs in text content")
            for url in found_urls[:50]:  # Limit to avoid too many
                doc_id = self.extract_document_id(url)
                if doc_id and doc_id not in seen_ids:
                    seen_ids.add(doc_id)
                    documents.append({
                        'document_id': doc_id,
                        'title': f'Document {doc_id}',
                        'url': url
                    })
        
        # Process links found via href
        for link in links:
            href = link.get('href', '')
            if '/laws/show/' in href:
                full_url = urljoin(self.base_url, href)
                title = link.get_text(strip=True) or link.get('title', '') or link.get('data-title', '')
                
                doc_id = self.extract_document_id(full_url)
                if doc_id and doc_id not in seen_ids:
                    seen_ids.add(doc_id)
                    
                    # Try to extract additional info from parent elements
                    parent = link.parent
                    doc_number = None
                    doc_date = None
                    
                    # Look for document number and date in nearby text
                    if parent:
                        parent_text = parent.get_text()
                        number_match = re.search(r'№\s*([0-9IVX]+(?:-[IVX]+)?)', parent_text)
                        if number_match:
                            doc_number = number_match.group(1)
                        
                        date_match = re.search(r'(\d{1,2}\.\d{1,2}\.\d{4})', parent_text)
                        if date_match:
                            doc_date = date_match.group(1)
                    
                    documents.append({
                        'document_id': doc_id,
                        'title': title or f'Document {doc_id}',
                        'url': full_url,
                        'document_number': doc_number,
                        'date': doc_date
                    })
        
        if self.verbose:
            self.logger.debug(f"Parsed {len(documents)} documents from HTML")
            if len(documents) == 0 and len(html) > 1000:
                # Debug: save a sample of HTML
                self.logger.debug(f"HTML sample (first 500 chars): {html[:500]}")
        
        return documents
    
    def fetch_document_details(self, document_url):
        """Fetch detailed information about a specific document"""
        try:
            # Use print version for better text extraction (contains full text)
            # Format: /laws/show/2341-14/print
            base_url = document_url.split('#')[0].split('?')[0]  # Remove anchors and params
            if not base_url.endswith('/print'):
                print_url = base_url + '/print'
            else:
                print_url = base_url
            
            # Try print version first (has full text)
            response = self._make_request(print_url, f"Fetching document (print version)")
            
            # If print version fails, try regular URL
            if response.status_code != 200:
                response = self._make_request(document_url, f"Fetching document")
            if response.status_code != 200:
                if response.status_code == 429:
                    self.logger.warning(f"⚠️  Rate limit hit for {document_url}")
                    time.sleep(60)
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract document metadata
            metadata = {}
            
            # Try to find document number, date, type, etc.
            title_elem = soup.find('h1') or soup.find('title')
            if title_elem:
                metadata['title'] = title_elem.get_text(strip=True)
            
            # Look for document number pattern (e.g., "2341-III")
            number_match = re.search(r'№\s*([0-9IVX]+(?:-[IVX]+)?)', response.text)
            if number_match:
                metadata['document_number'] = number_match.group(1)
            
            # Look for date pattern
            date_match = re.search(r'від\s+(\d{1,2}\.\d{1,2}\.\d{4})', response.text)
            if date_match:
                metadata['date'] = date_match.group(1)
            
            # Look for edition date
            edition_match = re.search(r'Редакція від\s+(\d{1,2}\.\d{1,2}\.\d{4})', response.text)
            if edition_match:
                metadata['edition_date'] = edition_match.group(1)
            
            # Extract document type
            type_match = re.search(r'(Кодекс|Закон|Постанова|Указ|Розпорядження)', response.text)
            if type_match:
                metadata['document_type'] = type_match.group(1)
            
            # Extract main content - try multiple strategies
            content = ''
            
            # Strategy 1: For print version, get body content directly
            if '/print' in print_url:
                body = soup.find('body')
                if body:
                    # Remove UI elements
                    for element in body.find_all(['script', 'style', 'nav', 'header', 'footer', 'button', 'form', 'link', 'meta']):
                        element.decompose()
                    # Get all text - less aggressive filtering for print versions
                    all_text = body.get_text(separator='\n', strip=True)
                    # Filter out UI elements and keep legal content
                    lines = all_text.split('\n')
                    filtered_lines = []
                    for line in lines:
                        stripped = line.strip()
                        # Keep: any non-empty line that's not just UI text
                        # More permissive for print versions
                        if stripped and len(stripped) > 0:
                            # Skip obvious UI elements
                            ui_keywords = ['Друкувати', 'Допомога', 'Шрифт:', 'mouse wheel', 'Ctrl +']
                            if not any(keyword in stripped for keyword in ui_keywords):
                                filtered_lines.append(line)
                    content = '\n'.join(filtered_lines)
            
            # Strategy 2: Find main content area (for regular pages)
            if not content or len(content) < 1000:
                main_content = soup.find('main')
                if main_content:
                    # Remove navigation, scripts, and other non-content elements
                    for element in main_content.find_all(['script', 'style', 'nav', 'header', 'footer', 'button', 'form']):
                        element.decompose()
                    content = main_content.get_text(separator='\n', strip=True)
            
            # Strategy 3: If no main, look for article/section content
            if not content or len(content) < 1000:
                content_divs = soup.find_all(['div', 'article', 'section'], 
                                           class_=re.compile(r'content|text|document|article', re.I))
                content = '\n'.join([div.get_text(separator='\n', strip=True) for div in content_divs])
            
            # Strategy 4: Get all paragraph text
            if not content or len(content) < 1000:
                paragraphs = soup.find_all('p')
                content = '\n'.join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20])
            
            # Clean up content
            if content:
                # Remove excessive whitespace
                content = re.sub(r'\n{3,}', '\n\n', content)
                # Remove common UI messages
                ui_patterns = [
                    r'Ваш броузер застарів.*?Safari\.',
                    r'Відбувається форматування тексту.*?заново',
                    r'Експортування великих файлів.*?часу!',
                    r'Потрібно включити javascript.*?замовчання',
                    r'Друкувати.*?mouse wheel',
                ]
                for pattern in ui_patterns:
                    content = re.sub(pattern, '', content, flags=re.DOTALL)
                # Clean up again
                content = re.sub(r'\n{3,}', '\n\n', content).strip()
            
            # Count articles/sections if it's a code or law
            if 'кодекс' in metadata.get('title', '').lower() or 'кодекс' in content.lower()[:500]:
                article_count = len(re.findall(r'Стаття\s+\d+', content))
                if article_count > 0:
                    metadata['article_count'] = article_count
            
            return {
                'content': content[:500000],  # Increased limit to 500KB for large documents
                'metadata': json.dumps(metadata, ensure_ascii=False)
            }
        
        except Exception as e:
            self.logger.debug(f"Error fetching document {document_url}: {e}")
            with self.stats_lock:
                self.stats['errors'] += 1
            return None
    
    def save_document(self, document_data):
        """Save document to database (thread-safe)"""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO documents 
                    (document_id, title, document_type, document_number, date, status, url, content, metadata, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    document_data.get('document_id'),
                    document_data.get('title'),
                    document_data.get('document_type'),
                    document_data.get('document_number'),
                    document_data.get('date'),
                    document_data.get('status', 'active'),
                    document_data.get('url'),
                    document_data.get('content'),
                    document_data.get('metadata')
                ))
                conn.commit()
                return True
            except sqlite3.Error as e:
                self.logger.error(f"Database error: {e}")
                return False
            finally:
                conn.close()
    
    def document_exists(self, document_id):
        """Check if document already exists (thread-safe)"""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM documents WHERE document_id = ?', (document_id,))
            exists = cursor.fetchone() is not None
            conn.close()
            return exists
    
    def download_single_document(self, doc):
        """Download a single document (for threading)"""
        doc_id = doc.get('document_id')
        if not doc_id:
            return None
        
        # Check if already downloaded
        if self.document_exists(doc_id):
            with self.stats_lock:
                self.stats['skipped'] += 1
            if self.verbose:
                self.logger.debug(f"⏭️  Skipping {doc_id} (already downloaded)")
            return None
        
        # Fetch document details
        if self.verbose:
            self.logger.info(f"⬇️  Downloading: {doc.get('title', doc_id)[:60]}...")
        
        details = self.fetch_document_details(doc['url'])
        
        if details:
            doc.update(details)
            if self.save_document(doc):
                with self.stats_lock:
                    self.stats['successful_downloads'] += 1
                if self.verbose:
                    self.logger.info(f"✅ Saved: {doc_id}")
                return doc
            else:
                with self.stats_lock:
                    self.stats['errors'] += 1
                self.logger.warning(f"❌ Failed to save: {doc_id}")
        else:
            with self.stats_lock:
                self.stats['errors'] += 1
            if self.verbose:
                self.logger.debug(f"⚠️  Could not fetch details for: {doc_id}")
        
        return None
    
    def _print_progress(self):
        """Print progress statistics"""
        elapsed = time.time() - self.stats['start_time']
        with self.stats_lock:
            stats = self.stats.copy()
        
        rate = stats['total_requests'] / elapsed if elapsed > 0 else 0
        docs_per_sec = stats['successful_downloads'] / elapsed if elapsed > 0 else 0
        
        self.logger.info("=" * 80)
        self.logger.info("📊 PROGRESS STATISTICS")
        self.logger.info("=" * 80)
        self.logger.info(f"   ✅ Downloaded: {stats['successful_downloads']}")
        self.logger.info(f"   ⏭️  Skipped: {stats['skipped']}")
        self.logger.info(f"   ❌ Errors: {stats['errors']}")
        self.logger.info(f"   🌐 Total Requests: {stats['total_requests']}")
        self.logger.info(f"   ⚠️  Rate Limit Hits: {stats['rate_limit_hits']}")
        self.logger.info(f"   ⏱️  Elapsed Time: {elapsed/60:.1f} minutes")
        self.logger.info(f"   📈 Request Rate: {rate:.2f} req/sec")
        self.logger.info(f"   📈 Download Rate: {docs_per_sec:.2f} docs/sec")
        self.logger.info(f"   📊 Current Rate Limit: {self.rate_limiter.get_current_rate()}/{self.rate_limiter.max_requests} req/min")
        self.logger.info("=" * 80)
    
    def download_documents(self, max_documents=None):
        """
        Main method to download documents using multi-threading
        max_documents: Limit number of documents to download (None for all)
        """
        self.logger.info("🚀 Starting document download...")
        initial_count = self.get_document_count()
        self.logger.info(f"📊 Current database count: {initial_count}")
        
        page = 1
        errors = 0
        document_queue = Queue()
        
        # Start progress reporting thread
        def progress_reporter():
            while True:
                time.sleep(30)  # Report every 30 seconds
                self._print_progress()
        
        progress_thread = threading.Thread(target=progress_reporter, daemon=True)
        progress_thread.start()
        
        # Collect documents from pages
        self.logger.info("📄 Collecting document list...")
        while True:
            if max_documents and self.stats['successful_downloads'] >= max_documents:
                break
            
            self.logger.info(f"📄 Fetching page {page}...")
            html = self.fetch_popular_documents_page(page)
            
            if not html:
                self.logger.warning(f"⚠️  No content received for page {page}")
                errors += 1
                if errors > 3:
                    self.logger.error("❌ Too many errors, stopping")
                    break
                page += 1
                continue
            
            documents = self.parse_document_list(html)
            
            if not documents:
                self.logger.warning(f"⚠️  No documents found on page {page}")
                page += 1
                if page > 100:  # Safety limit
                    break
                continue
            
            self.logger.info(f"📋 Found {len(documents)} documents on page {page}")
            
            # Add documents to queue
            for doc in documents:
                if max_documents and self.stats['successful_downloads'] >= max_documents:
                    break
                document_queue.put(doc)
            
            if len(documents) == 0:
                self.logger.info("📄 No more documents found")
                break
            
            page += 1
        
        # Download documents using thread pool
        self.logger.info(f"⬇️  Starting download with {self.max_workers} workers...")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            while not document_queue.empty():
                if max_documents and self.stats['successful_downloads'] >= max_documents:
                    break
                
                doc = document_queue.get()
                future = executor.submit(self.download_single_document, doc)
                futures.append(future)
            
            # Wait for completion
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    self.logger.error(f"❌ Thread error: {e}")
                    with self.stats_lock:
                        self.stats['errors'] += 1
        
        # Final statistics
        self._print_progress()
        final_count = self.get_document_count()
        new_documents = final_count - initial_count
        
        self.logger.info("")
        self.logger.info("=" * 80)
        self.logger.info("✅ DOWNLOAD COMPLETE!")
        self.logger.info("=" * 80)
        self.logger.info(f"   📊 New documents downloaded: {new_documents}")
        self.logger.info(f"   📊 Total in database: {final_count}")
        self.logger.info("=" * 80)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Download documents from zakon.rada.gov.ua',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Rate Limiting Rules:
  - Limit on pages per minute from single IP
  - Excessive requests = temporary denial (several minutes)
  - Repeated violations = 24h or permanent suspension
  - Peak hours (10:00-13:00, 14:00-17:00) may timeout after 10s

Recommended Settings:
  - Workers: 3-5 (higher may trigger rate limits)
  - Requests/min: 20-30 (conservative), 30-40 (moderate), 40+ (risky)
        '''
    )
    parser.add_argument('--max', type=int, help='Maximum number of documents to download')
    parser.add_argument('--db', default='documents.db', help='Database file path')
    parser.add_argument('--test', action='store_true', help='Test mode: download only 10 documents')
    parser.add_argument('--workers', type=int, default=3, help='Number of concurrent workers (default: 3)')
    parser.add_argument('--requests-per-minute', type=int, default=30, 
                       help='Maximum requests per minute (default: 30, recommended: 20-40)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    downloader = DocumentDownloader(
        db_path=args.db,
        max_workers=args.workers,
        requests_per_minute=args.requests_per_minute,
        verbose=args.verbose
    )
    
    if args.test:
        downloader.logger.info("🧪 Running in TEST mode (10 documents)")
        downloader.download_documents(max_documents=10)
    else:
        downloader.download_documents(max_documents=args.max)

if __name__ == '__main__':
    main()

