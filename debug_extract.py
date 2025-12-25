#!/usr/bin/env python3
"""Debug content extraction"""
import sys
from download_documents import DocumentDownloader

url = 'https://zakon.rada.gov.ua/laws/show/2341-14'
downloader = DocumentDownloader(verbose=True)

print("Fetching document details...")
details = downloader.fetch_document_details(url)

if details:
    print(f"\n✅ Got details:")
    print(f"   Content length: {len(details.get('content', '')):,} chars")
    print(f"   Metadata: {details.get('metadata', 'N/A')}")
    if details.get('content'):
        print(f"\nFirst 500 chars of content:")
        print("="*60)
        print(details['content'][:500])
        print("="*60)
    else:
        print("\n❌ Content is empty!")
else:
    print("\n❌ Failed to fetch details")

