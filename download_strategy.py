#!/usr/bin/env python3
"""
Smart download strategy for Ukrainian law documents for ML fine-tuning

Strategy:
1. Download all codes (Кодекси) - foundational documents
2. Download top N popular documents
3. Download recent documents (last 2 years)
4. Keep API access for updates and specific queries
"""
import argparse
import sqlite3
import re
from download_all_popular import PopularDocumentsDownloader
from extract_with_playwright import extract_document_with_playwright, save_to_database
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

class SmartDownloadStrategy:
    def __init__(self, db_path='documents.db', verbose=False):
        self.db_path = db_path
        self.base_url = 'https://zakon.rada.gov.ua'
        self.verbose = verbose
        self.downloader = PopularDocumentsDownloader(db_path=db_path, verbose=verbose)
    
    def download_all_codes(self):
        """Download all Кодекси (Codes) - most important for legal understanding"""
        print("=" * 80)
        print("STEP 1: Downloading all Кодекси (Codes)")
        print("=" * 80)
        
        # Known codes from the popular documents page
        codes = [
            '2341-14',  # Кримінальний кодекс
            '435-15',   # Цивільний кодекс
            '4651-17',  # Кримінальний процесуальний кодекс
            '1618-15',  # Цивільний процесуальний кодекс
            '2755-17',  # Податковий кодекс
            '80731-10', # Кодекс про адміністративні правопорушення
            '322-08',   # Кодекс законів про працю
            '4495-17',  # Митний кодекс
            # Add more as needed
        ]
        
        downloaded = 0
        for doc_id in codes:
            url = f"{self.base_url}/laws/show/{doc_id}"
            if not self.downloader.document_exists(doc_id):
                print(f"⬇️  Downloading code: {doc_id}")
                doc = {'document_id': doc_id, 'url': url, 'title': f'Code {doc_id}'}
                result = self.downloader.download_single_document(doc)
                if result:
                    downloaded += 1
            else:
                print(f"⏭️  Code {doc_id} already downloaded")
        
        print(f"\n✅ Downloaded {downloaded} new codes")
        return downloaded
    
    def download_top_popular(self, n=1000):
        """Download top N popular documents"""
        print("\n" + "=" * 80)
        print(f"STEP 2: Downloading top {n} popular documents")
        print("=" * 80)
        
        self.downloader.download_all(max_documents=n)
    
    def download_by_type(self, doc_type='Кодекс', max_docs=100):
        """Download documents by type (Кодекс, Закон, Постанова, etc.)"""
        print(f"\n📄 Downloading documents of type: {doc_type}")
        # Implementation: search and filter by type
        pass
    
    def get_dataset_stats(self):
        """Get statistics about downloaded dataset"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total documents
        cursor.execute('SELECT COUNT(*) FROM documents')
        total = cursor.fetchone()[0]
        
        # Documents with content
        cursor.execute('SELECT COUNT(*) FROM documents WHERE LENGTH(content) > 1000')
        with_content = cursor.fetchone()[0]
        
        # Total content size
        cursor.execute('SELECT SUM(LENGTH(content)) FROM documents')
        total_size = cursor.fetchone()[0] or 0
        
        # By document type
        cursor.execute('''
            SELECT document_type, COUNT(*) 
            FROM documents 
            WHERE document_type IS NOT NULL 
            GROUP BY document_type 
            ORDER BY COUNT(*) DESC
        ''')
        by_type = cursor.fetchall()
        
        # Articles count (for codes)
        cursor.execute('''
            SELECT SUM(CAST(json_extract(metadata, '$.article_count') AS INTEGER))
            FROM documents
            WHERE json_extract(metadata, '$.article_count') IS NOT NULL
        ''')
        total_articles = cursor.fetchone()[0] or 0
        
        conn.close()
        
        print("\n" + "=" * 80)
        print("📊 DATASET STATISTICS")
        print("=" * 80)
        print(f"   Total documents: {total:,}")
        print(f"   Documents with content: {with_content:,}")
        print(f"   Total content size: {total_size / 1024 / 1024:.1f} MB")
        print(f"   Total articles: {total_articles:,}")
        print(f"\n   By document type:")
        for doc_type, count in by_type[:10]:
            print(f"     {doc_type}: {count:,}")
        print("=" * 80)
        
        return {
            'total': total,
            'with_content': with_content,
            'total_size_mb': total_size / 1024 / 1024,
            'total_articles': total_articles
        }
    
    def export_for_training(self, output_file='training_data.txt', min_length=1000):
        """Export documents for ML training"""
        print(f"\n📤 Exporting documents for training to {output_file}")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT title, content, document_type, document_number
            FROM documents
            WHERE LENGTH(content) >= ?
            ORDER BY 
                CASE document_type 
                    WHEN 'Кодекс' THEN 1
                    WHEN 'Закон' THEN 2
                    ELSE 3
                END,
                title
        ''', (min_length,))
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for row in cursor:
                title, content, doc_type, doc_number = row
                f.write(f"=== {title} ===\n")
                if doc_type:
                    f.write(f"Type: {doc_type}\n")
                if doc_number:
                    f.write(f"Number: {doc_number}\n")
                f.write(f"\n{content}\n\n")
                f.write("=" * 80 + "\n\n")
        
        conn.close()
        print(f"✅ Exported to {output_file}")

def main():
    parser = argparse.ArgumentParser(
        description='Smart download strategy for Ukrainian law documents',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Recommended workflow for ML fine-tuning:

1. Download all codes (foundational):
   python3 download_strategy.py --codes

2. Download top 1000 popular documents:
   python3 download_strategy.py --top-popular 1000

3. Check dataset statistics:
   python3 download_strategy.py --stats

4. Export for training:
   python3 download_strategy.py --export training_data.txt

5. For ongoing updates, use online API access
        '''
    )
    parser.add_argument('--codes', action='store_true', help='Download all codes')
    parser.add_argument('--top-popular', type=int, help='Download top N popular documents')
    parser.add_argument('--stats', action='store_true', help='Show dataset statistics')
    parser.add_argument('--export', type=str, help='Export documents to file for training')
    parser.add_argument('--db', default='documents.db', help='Database file path')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    strategy = SmartDownloadStrategy(db_path=args.db, verbose=args.verbose)
    
    if args.codes:
        strategy.download_all_codes()
    
    if args.top_popular:
        strategy.download_top_popular(args.top_popular)
    
    if args.stats:
        strategy.get_dataset_stats()
    
    if args.export:
        strategy.export_for_training(args.export)
    
    if not any([args.codes, args.top_popular, args.stats, args.export]):
        parser.print_help()

if __name__ == '__main__':
    main()

