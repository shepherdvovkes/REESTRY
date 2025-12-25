#!/usr/bin/env python3
"""
Extract full text from a document URL
"""
import requests
from bs4 import BeautifulSoup
import re
import sys

def extract_document_text(url):
    """Extract full text content from a document page"""
    try:
        # Use print version for better text extraction (contains full text)
        # Format: /laws/show/2341-14/print
        base_url = url.split('#')[0].split('?')[0]  # Remove anchors and params
        if not base_url.endswith('/print'):
            print_url = base_url + '/print'
        else:
            print_url = base_url
        
        # Try print version first
        response = requests.get(print_url, timeout=60, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7',
        })
        
        # If print version fails, try regular URL
        if response.status_code != 200:
            response = requests.get(url, timeout=60, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7',
            })
            if response.status_code != 200:
                print(f"Error: Status code {response.status_code}")
                return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract metadata
        title = soup.find('h1')
        title_text = title.get_text(strip=True) if title else 'Unknown'
        
        # Extract document number and date from page
        doc_number = None
        doc_date = None
        number_match = re.search(r'№\s*([0-9IVX]+(?:-[IVX]+)?)', response.text)
        if number_match:
            doc_number = number_match.group(1)
        
        date_match = re.search(r'від\s+(\d{1,2}\.\d{1,2}\.\d{4})', response.text)
        if date_match:
            doc_date = date_match.group(1)
        
        # Extract main content - try multiple strategies
        text = ''
        
        # Strategy 1: For print version, get body content directly (best for full text)
        if '/print' in print_url:
            body = soup.find('body')
            if body:
                # Remove UI elements
                for element in body.find_all(['script', 'style', 'nav', 'header', 'footer', 'button', 'form', 'link', 'meta']):
                    element.decompose()
                # Get all text
                all_text = body.get_text(separator='\n', strip=True)
                # Filter out UI elements and keep legal content
                lines = all_text.split('\n')
                filtered_lines = []
                for line in lines:
                    stripped = line.strip()
                    # Keep: long lines, article markers, section markers, numbers
                    if (len(stripped) > 10 or 
                        re.match(r'^Стаття\s+\d+', stripped) or
                        re.match(r'^Розділ\s+\d+', stripped) or
                        re.match(r'^Частина\s+[IVX]+', stripped, re.I) or
                        (stripped.isdigit() and len(stripped) < 5)):
                        filtered_lines.append(line)
                text = '\n'.join(filtered_lines)
        
        # Strategy 2: Find main content area (for regular pages)
        if not text or len(text) < 5000:
            main_content = soup.find('main')
            if main_content:
                # Remove non-content elements
                for element in main_content.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside', 'button', 'form']):
                    element.decompose()
                text = main_content.get_text(separator='\n', strip=True)
        
        # Strategy 3: If main is too short, look for content in body
        if not text or len(text) < 5000:
            body = soup.find('body')
            if body:
                # Remove scripts, styles, navigation
                for element in body.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside', 'button', 'form', 'link', 'meta']):
                    element.decompose()
                # Get all text but filter out navigation/UI
                all_text = body.get_text(separator='\n', strip=True)
                # Filter lines - keep longer lines and article markers
                lines = all_text.split('\n')
                filtered_lines = []
                for line in lines:
                    stripped = line.strip()
                    # Keep if: long enough, is article marker, is number, or contains legal text
                    if (len(stripped) > 10 or 
                        re.match(r'^Стаття\s+\d+', stripped) or
                        re.match(r'^Розділ\s+\d+', stripped) or
                        re.match(r'^Частина\s+[IVX]+', stripped, re.I) or
                        stripped.isdigit() and len(stripped) < 5):
                        filtered_lines.append(line)
                text = '\n'.join(filtered_lines)
        
        # Clean up text
        if text:
            # Remove excessive whitespace
            text = re.sub(r'\n{3,}', '\n\n', text)
            # Remove common UI elements
            ui_patterns = [
                r'Ваш броузер застарів.*?Safari\.',
                r'Відбувається форматування тексту.*?заново',
                r'Експортування великих файлів.*?часу!',
                r'Виберіть формат файлу.*?Завантажити',
                r'Поділитися.*?Запам\'ятати',
                r'Повідомити про помилку.*?Скасувати',
            ]
            for pattern in ui_patterns:
                text = re.sub(pattern, '', text, flags=re.DOTALL)
            # Clean up again
            text = re.sub(r'\n{3,}', '\n\n', text).strip()
        
        # Count articles if it's a code
        article_count = 0
        if 'кодекс' in title_text.lower():
            article_count = len(re.findall(r'Стаття\s+\d+', text))
        
        return {
            'title': title_text,
            'document_number': doc_number,
            'date': doc_date,
            'text': text,
            'length': len(text),
            'word_count': len(text.split()),
            'article_count': article_count
        }
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 extract_text.py <document_url> [output_file]")
        print("Example: python3 extract_text.py https://zakon.rada.gov.ua/laws/show/2341-14")
        sys.exit(1)
    
    url = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f"Extracting text from: {url}")
    result = extract_document_text(url)
    
    if result:
        print(f"\n✅ Extracted:")
        print(f"   Title: {result['title']}")
        print(f"   Length: {result['length']:,} characters")
        print(f"   Words: {result['word_count']:,}")
        print(f"\n📄 First 500 characters:")
        print("=" * 60)
        print(result['text'][:500])
        print("=" * 60)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"Title: {result['title']}\n")
                f.write("=" * 60 + "\n\n")
                f.write(result['text'])
            print(f"\n💾 Saved to: {output_file}")
        else:
            print(f"\n📄 Full text (first 2000 chars):")
            print("=" * 60)
            print(result['text'][:2000])
            print("=" * 60)
            print(f"\n... ({result['length'] - 2000:,} more characters)")
    else:
        print("❌ Failed to extract text")

if __name__ == '__main__':
    main()

