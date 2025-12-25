#!/usr/bin/env python3
"""
Download all documents from the popular documents page using Playwright
https://zakon.rada.gov.ua/laws/main/d
"""
import sys
import re
import sqlite3
import json
import time
import argparse
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from queue import Queue

class PopularDocumentsDownloader:
    def __init__(self, db_path='documents.db', max_workers=2, verbose=False):
        self.db_path = db_path
        self.base_url = 'https://zakon.rada.gov.ua'
        self.max_workers = max_workers
        self.verbose = verbose
        self.db_lock = threading.Lock()
        
        # Statistics
        self.stats = {
            'total_found': 0,
            'successful_downloads': 0,
            'skipped': 0,
            'errors': 0,
            'start_time': time.time()
        }
        self.stats_lock = threading.Lock()
        
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database"""
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
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_document_id ON documents(document_id)')
        conn.commit()
        conn.close()
    
    def document_exists(self, document_id):
        """Check if document already exists"""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM documents WHERE document_id = ?', (document_id,))
            exists = cursor.fetchone() is not None
            conn.close()
            return exists
    
    
    def get_all_pages(self, base_url):
        """Get all paginated pages and extract document links"""
        all_links = []
        page = 1
        
        print(f"📄 Extracting document links from all pages...")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page_obj = browser.new_page()
            
            while True:
                if page == 1:
                    page_url = base_url
                else:
                    # Try different pagination formats
                    page_url = f"{base_url}?page={page}"
                
                try:
                    print(f"🌐 Loading page {page}: {page_url}")
                    page_obj.goto(page_url, wait_until='networkidle', timeout=60000)
                    page_obj.wait_for_timeout(3000)
                    
                    html_content = page_obj.content()
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # Extract document links from this page
                    links = []
                    seen_ids = set()
                    
                    for a_tag in soup.find_all('a', href=True):
                        href = a_tag.get('href', '')
                        if '/laws/show/' in href:
                            if href.startswith('http'):
                                full_url = href
                            else:
                                full_url = self.base_url + href
                            
                            match = re.search(r'/laws/show/([^/]+)', full_url)
                            if match:
                                doc_id = match.group(1)
                                if doc_id not in seen_ids:
                                    seen_ids.add(doc_id)
                                    title = a_tag.get_text(strip=True)
                                    if not title or len(title) < 5:
                                        parent = a_tag.parent
                                        if parent:
                                            title = parent.get_text(strip=True)
                                    
                                    links.append({
                                        'document_id': doc_id,
                                        'url': full_url.split('#')[0].split('?')[0],
                                        'title': title or f'Document {doc_id}'
                                    })
                    
                    if not links:
                        print(f"⚠️  No links found on page {page}, stopping")
                        break
                    
                    print(f"📋 Page {page}: Found {len(links)} documents")
                    all_links.extend(links)
                    
                    # Check for next page link - look for "наступна" (next) link
                    next_link = soup.find('a', string=re.compile(r'наступна|next', re.I))
                    if not next_link:
                        # Check for page number links in pagination
                        pagination = soup.find_all('a', href=True)
                        has_next = False
                        for link in pagination:
                            href = link.get('href', '')
                            link_text = link.get_text(strip=True)
                            # Check if there's a page number higher than current
                            if 'page' in href.lower() or 'd20' in href:
                                page_match = re.search(r'page[=_]?(\d+)', href, re.I)
                                if page_match:
                                    page_num = int(page_match.group(1))
                                    if page_num > page:
                                        has_next = True
                                        break
                            # Check for "наступна" in text
                            if 'наступна' in link_text.lower() or 'next' in link_text.lower():
                                has_next = True
                                break
                        
                        if not has_next:
                            print(f"📄 No more pages found, stopping at page {page}")
                            break
                    
                    page += 1
                    time.sleep(2)  # Rate limiting between page fetches
                    
                except Exception as e:
                    print(f"❌ Error fetching page {page}: {e}")
                    if page == 1:
                        browser.close()
                        raise  # Fail if first page fails
                    break
            
            browser.close()
        
        return all_links
    
    def extract_document_with_playwright(self, url):
        """Extract document content using Playwright"""
        # Use print version for better extraction
        base_url = url.split('#')[0].split('?')[0]
        print_url = base_url + '/print' if not base_url.endswith('/print') else base_url
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # Navigate and wait
                page.goto(print_url, wait_until='networkidle', timeout=60000)
                page.wait_for_timeout(2000)
                
                html_content = page.content()
                browser.close()
            
            soup = BeautifulSoup(html_content, 'html.parser')
            body = soup.find('body')
            
            if not body:
                return None
            
            # Remove UI elements
            for element in body.find_all(['script', 'style', 'nav', 'header', 'footer', 'button', 'form', 'link', 'meta']):
                element.decompose()
            
            for element in body.find_all(class_=re.compile(r'print|help|font|size|ui|toolbar|menu', re.I)):
                element.decompose()
            for element in body.find_all(id=re.compile(r'print|help|font|size|ui|toolbar|menu', re.I)):
                element.decompose()
            
            # Extract text
            all_text = body.get_text(separator='\n', strip=True)
            lines = all_text.split('\n')
            filtered_lines = []
            for line in lines:
                stripped = line.strip()
                if stripped and len(stripped) > 0:
                    if len(stripped) <= 20:
                        ui_only = ['mouse wheel', 'Ctrl +', 'Шрифт:']
                        if any(keyword in stripped for keyword in ui_only):
                            continue
                    filtered_lines.append(line)
            
            content = '\n'.join(filtered_lines)
            
            # Extract metadata
            title_elem = soup.find('h1') or soup.find('title')
            title = title_elem.get_text(strip=True) if title_elem else 'Unknown'
            
            number_match = re.search(r'№\s*([0-9IVX]+(?:-[IVX]+)?)', html_content)
            doc_number = number_match.group(1) if number_match else None
            
            date_match = re.search(r'від\s+(\d{1,2}\.\d{1,2}\.\d{4})', html_content)
            doc_date = date_match.group(1) if date_match else None
            
            type_match = re.search(r'(Кодекс|Закон|Постанова|Указ|Розпорядження)', html_content)
            doc_type = type_match.group(1) if type_match else None
            
            article_count = len(re.findall(r'Стаття\s+\d+', content))
            
            return {
                'title': title,
                'document_number': doc_number,
                'date': doc_date,
                'document_type': doc_type,
                'content': content,
                'article_count': article_count
            }
        except Exception as e:
            if self.verbose:
                print(f"❌ Error extracting {url}: {e}")
            return None
    
    def save_document(self, doc_data):
        """Save document to database"""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            metadata = {
                'title': doc_data.get('title'),
                'document_number': doc_data.get('document_number'),
                'date': doc_data.get('date'),
                'document_type': doc_data.get('document_type'),
                'article_count': doc_data.get('article_count', 0)
            }
            
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO documents 
                    (document_id, title, document_type, document_number, date, status, url, content, metadata, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    doc_data['document_id'],
                    doc_data.get('title'),
                    doc_data.get('document_type'),
                    doc_data.get('document_number'),
                    doc_data.get('date'),
                    'active',
                    doc_data['url'],
                    doc_data.get('content', '')[:500000],  # Limit to 500KB
                    json.dumps(metadata, ensure_ascii=False)
                ))
                conn.commit()
                return True
            except Exception as e:
                if self.verbose:
                    print(f"❌ Database error: {e}")
                return False
            finally:
                conn.close()
    
    def download_single_document(self, doc):
        """Download a single document"""
        doc_id = doc['document_id']
        
        # Check if already exists
        if self.document_exists(doc_id):
            with self.stats_lock:
                self.stats['skipped'] += 1
            if self.verbose:
                print(f"⏭️  Skipping {doc_id} (already downloaded)")
            return None
        
        if self.verbose:
            print(f"⬇️  Downloading: {doc.get('title', doc_id)[:60]}...")
        
        # Extract content
        content_data = self.extract_document_with_playwright(doc['url'])
        
        if not content_data:
            with self.stats_lock:
                self.stats['errors'] += 1
            return None
        
        # Merge with doc data
        doc.update(content_data)
        
        # Save to database
        if self.save_document(doc):
            with self.stats_lock:
                self.stats['successful_downloads'] += 1
            if self.verbose:
                print(f"✅ Saved: {doc_id}")
            return doc
        else:
            with self.stats_lock:
                self.stats['errors'] += 1
            return None
    
    def print_progress(self):
        """Print progress statistics"""
        elapsed = time.time() - self.stats['start_time']
        with self.stats_lock:
            stats = self.stats.copy()
        
        rate = stats['successful_downloads'] / elapsed if elapsed > 0 else 0
        
        print("\n" + "=" * 80)
        print("📊 PROGRESS STATISTICS")
        print("=" * 80)
        print(f"   ✅ Downloaded: {stats['successful_downloads']}")
        print(f"   ⏭️  Skipped: {stats['skipped']}")
        print(f"   ❌ Errors: {stats['errors']}")
        print(f"   📋 Total Found: {stats['total_found']}")
        print(f"   ⏱️  Elapsed Time: {elapsed/60:.1f} minutes")
        print(f"   📈 Download Rate: {rate:.2f} docs/min")
        print("=" * 80 + "\n")
    
    def download_all(self, max_documents=None, max_pages=None):
        """Download all documents from popular documents page"""
        base_url = f"{self.base_url}/laws/main/d"
        
        print("🚀 Starting download of all popular documents...")
        print(f"📄 Source: {base_url}")
        print(f"⚙️  Workers: {self.max_workers}")
        print()
        
        # Step 1: Extract all document links
        print("=" * 80)
        print("STEP 1: Extracting document links")
        print("=" * 80)
        
        all_links = self.get_all_pages(base_url)
        
        if max_pages:
            # Limit to first N pages worth of links
            links_per_page = 50  # Approximate
            max_links = max_pages * links_per_page
            all_links = all_links[:max_links]
        
        with self.stats_lock:
            self.stats['total_found'] = len(all_links)
        
        print(f"\n✅ Found {len(all_links)} documents total")
        
        if max_documents:
            all_links = all_links[:max_documents]
            print(f"📊 Limiting to {max_documents} documents")
        
        # Step 2: Download documents
        print("\n" + "=" * 80)
        print("STEP 2: Downloading documents")
        print("=" * 80)
        
        # Start progress reporting
        def progress_reporter():
            while True:
                time.sleep(30)
                self.print_progress()
        
        progress_thread = threading.Thread(target=progress_reporter, daemon=True)
        progress_thread.start()
        
        # Download with thread pool
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self.download_single_document, doc) for doc in all_links]
            
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    if self.verbose:
                        print(f"❌ Thread error: {e}")
                    with self.stats_lock:
                        self.stats['errors'] += 1
        
        # Final statistics
        self.print_progress()
        print("✅ Download complete!")

def main():
    parser = argparse.ArgumentParser(
        description='Download all documents from popular documents page',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--max', type=int, help='Maximum number of documents to download')
    parser.add_argument('--max-pages', type=int, help='Maximum number of pages to process')
    parser.add_argument('--db', default='documents.db', help='Database file path')
    parser.add_argument('--test', action='store_true', help='Test mode: download only 10 documents')
    parser.add_argument('--workers', type=int, default=2, help='Number of concurrent workers (default: 2)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    downloader = PopularDocumentsDownloader(
        db_path=args.db,
        max_workers=args.workers,
        verbose=args.verbose
    )
    
    if args.test:
        downloader.download_all(max_documents=10)
    else:
        downloader.download_all(max_documents=args.max, max_pages=args.max_pages)

if __name__ == '__main__':
    main()

