#!/usr/bin/env python3
"""
Download a single document by URL
"""
import sys
from download_documents import DocumentDownloader
import re
import sqlite3

def extract_document_id(url):
    """Extract document ID from URL"""
    match = re.search(r'/laws/show/([^/]+)', url)
    if match:
        return match.group(1)
    return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 download_single.py <document_url>")
        print("Example: python3 download_single.py https://zakon.rada.gov.ua/laws/show/2341-14#Text")
        sys.exit(1)
    
    url = sys.argv[1]
    # Remove hash fragment for URL processing (but keep original for display)
    base_url = url.split('#')[0]
    
    print(f"📥 Downloading document from: {url}")
    
    # Initialize downloader
    downloader = DocumentDownloader(
        db_path='documents.db',
        max_workers=1,
        requests_per_minute=30,
        verbose=True
    )
    
    # Extract document ID
    doc_id = extract_document_id(base_url)
    if not doc_id:
        print(f"❌ Could not extract document ID from URL: {url}")
        sys.exit(1)
    
    print(f"📋 Document ID: {doc_id}")
    
    # Check if already exists
    if downloader.document_exists(doc_id):
        if '--force' not in sys.argv:
            print(f"ℹ️  Document {doc_id} already exists in database")
            print("   Use --force to re-download")
            # Check if content is empty
            conn = sqlite3.connect('documents.db')
            cursor = conn.cursor()
            cursor.execute('SELECT LENGTH(content) FROM documents WHERE document_id = ?', (doc_id,))
            result = cursor.fetchone()
            content_len = result[0] if result else 0
            conn.close()
            if content_len == 0:
                print(f"   ⚠️  Document exists but has no content. Re-downloading...")
            else:
                sys.exit(0)
        else:
            # Delete existing document if --force is used
            print(f"🗑️  Removing existing document {doc_id} (--force flag)")
            conn = sqlite3.connect('documents.db')
            cursor = conn.cursor()
            cursor.execute('DELETE FROM documents WHERE document_id = ?', (doc_id,))
            conn.commit()
            conn.close()
            print(f"   ✅ Removed existing document")
    
    # Prepare document data
    doc = {
        'document_id': doc_id,
        'title': f'Document {doc_id}',
        'url': base_url
    }
    
    # Download
    print(f"⬇️  Fetching document details...")
    result = downloader.download_single_document(doc)
    
    if result:
        print(f"\n✅ Successfully downloaded and saved!")
        print(f"   Document ID: {result.get('document_id')}")
        print(f"   Title: {result.get('title', 'N/A')}")
        if result.get('content'):
            content_len = len(result['content'])
            print(f"   Content length: {content_len:,} characters")
            print(f"   Content preview (first 200 chars):")
            print("   " + result['content'][:200].replace('\n', ' '))
    else:
        print(f"\n❌ Failed to download document")
        sys.exit(1)

if __name__ == '__main__':
    main()

