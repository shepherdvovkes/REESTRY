#!/usr/bin/env python3
"""
Extract document text using Playwright to render JavaScript
"""
import sys
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re
import sqlite3
import json
from datetime import datetime

def extract_document_with_playwright(url):
    """Extract document content using Playwright"""
    # Use print version for better extraction
    base_url = url.split('#')[0].split('?')[0]
    print_url = base_url + '/print' if not base_url.endswith('/print') else base_url
    
    print(f"🌐 Loading page with Playwright: {print_url}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Navigate and wait for content to load
        page.goto(print_url, wait_until='networkidle', timeout=60000)
        
        # Wait a bit more for any dynamic content
        page.wait_for_timeout(2000)
        
        # Get the rendered HTML
        html_content = page.content()
        browser.close()
    
    print(f"✅ Page loaded, HTML length: {len(html_content):,} chars")
    
    # Parse with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    body = soup.find('body')
    
    if not body:
        print("❌ No body found in HTML")
        return None
    
    # Remove UI elements
    for element in body.find_all(['script', 'style', 'nav', 'header', 'footer', 'button', 'form', 'link', 'meta']):
        element.decompose()
    
    # Remove elements with UI-related classes/IDs
    for element in body.find_all(class_=re.compile(r'print|help|font|size|ui|toolbar|menu', re.I)):
        element.decompose()
    for element in body.find_all(id=re.compile(r'print|help|font|size|ui|toolbar|menu', re.I)):
        element.decompose()
    
    # Extract all text
    all_text = body.get_text(separator='\n', strip=True)
    
    # Filter out very short UI-only lines
    lines = all_text.split('\n')
    filtered_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and len(stripped) > 0:
            # Only skip very short lines that are clearly UI
            if len(stripped) <= 20:
                ui_only = ['mouse wheel', 'Ctrl +', 'Шрифт:']
                if any(keyword in stripped for keyword in ui_only):
                    continue
            filtered_lines.append(line)
    
    content = '\n'.join(filtered_lines)
    
    # Extract metadata
    title_elem = soup.find('h1') or soup.find('title')
    title = title_elem.get_text(strip=True) if title_elem else 'Unknown'
    
    # Extract document number
    number_match = re.search(r'№\s*([0-9IVX]+(?:-[IVX]+)?)', html_content)
    doc_number = number_match.group(1) if number_match else None
    
    # Extract date
    date_match = re.search(r'від\s+(\d{1,2}\.\d{1,2}\.\d{4})', html_content)
    doc_date = date_match.group(1) if date_match else None
    
    # Extract document type
    type_match = re.search(r'(Кодекс|Закон|Постанова|Указ|Розпорядження)', html_content)
    doc_type = type_match.group(1) if type_match else None
    
    # Count articles
    article_count = len(re.findall(r'Стаття\s+\d+', content))
    
    return {
        'title': title,
        'document_number': doc_number,
        'date': doc_date,
        'document_type': doc_type,
        'content': content,
        'article_count': article_count
    }

def save_to_database(doc_id, data, url):
    """Save document to database"""
    conn = sqlite3.connect('documents.db')
    cursor = conn.cursor()
    
    metadata = {
        'title': data['title'],
        'document_number': data['document_number'],
        'date': data['date'],
        'document_type': data['document_type'],
        'article_count': data['article_count']
    }
    
    cursor.execute('''
        INSERT OR REPLACE INTO documents 
        (document_id, title, document_type, document_number, date, status, url, content, metadata, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (
        doc_id,
        data['title'],
        data['document_type'],
        data['document_number'],
        data['date'],
        'active',
        url,
        data['content'][:500000],  # Limit to 500KB
        json.dumps(metadata, ensure_ascii=False)
    ))
    
    conn.commit()
    conn.close()
    print(f"💾 Saved to database")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 extract_with_playwright.py <document_url>")
        print("Example: python3 extract_with_playwright.py https://zakon.rada.gov.ua/laws/show/2341-14#Text")
        sys.exit(1)
    
    url = sys.argv[1]
    base_url = url.split('#')[0].split('?')[0]
    
    # Extract document ID
    match = re.search(r'/laws/show/([^/]+)', base_url)
    if not match:
        print(f"❌ Could not extract document ID from URL: {url}")
        sys.exit(1)
    
    doc_id = match.group(1)
    print(f"📋 Document ID: {doc_id}")
    
    # Extract content
    data = extract_document_with_playwright(url)
    
    if not data:
        print("❌ Failed to extract content")
        sys.exit(1)
    
    print(f"\n✅ Extracted:")
    print(f"   Title: {data['title']}")
    print(f"   Content length: {len(data['content']):,} characters")
    print(f"   Articles found: {data['article_count']}")
    print(f"\n📄 Content preview (first 500 chars):")
    print("="*60)
    print(data['content'][:500])
    print("="*60)
    
    # Save to database
    save_to_database(doc_id, data, base_url)
    print(f"\n✅ Document {doc_id} downloaded and saved!")

if __name__ == '__main__':
    main()

