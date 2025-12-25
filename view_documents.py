#!/usr/bin/env python3
"""
View and search documents in the database
"""
import sqlite3
import sys
from datetime import datetime

def view_documents(db_path='documents.db', limit=20, search_term=None):
    """View documents from the database"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get total count
    cursor.execute('SELECT COUNT(*) FROM documents')
    total = cursor.fetchone()[0]
    
    print(f"📊 Total documents in database: {total}\n")
    
    # Build query
    if search_term:
        query = '''
            SELECT document_id, title, document_number, date, url, downloaded_at
            FROM documents
            WHERE title LIKE ? OR document_number LIKE ? OR content LIKE ?
            ORDER BY downloaded_at DESC
            LIMIT ?
        '''
        search_pattern = f'%{search_term}%'
        cursor.execute(query, (search_pattern, search_pattern, search_pattern, limit))
    else:
        query = '''
            SELECT document_id, title, document_number, date, url, downloaded_at
            FROM documents
            ORDER BY downloaded_at DESC
            LIMIT ?
        '''
        cursor.execute(query, (limit,))
    
    documents = cursor.fetchall()
    
    if not documents:
        print("No documents found.")
        conn.close()
        return
    
    print(f"Showing {len(documents)} documents:\n")
    print("=" * 100)
    
    for doc in documents:
        doc_id, title, number, date, url, downloaded = doc
        print(f"\n📄 ID: {doc_id}")
        print(f"   Title: {title}")
        if number:
            print(f"   Number: {number}")
        if date:
            print(f"   Date: {date}")
        print(f"   URL: {url}")
        print(f"   Downloaded: {downloaded}")
        print("-" * 100)
    
    conn.close()

def get_statistics(db_path='documents.db'):
    """Get database statistics"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM documents')
    total = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM documents WHERE date IS NOT NULL')
    with_dates = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM documents WHERE content IS NOT NULL AND content != ""')
    with_content = cursor.fetchone()[0]
    
    cursor.execute('SELECT MIN(downloaded_at), MAX(downloaded_at) FROM documents')
    date_range = cursor.fetchone()
    
    print("📊 Database Statistics")
    print("=" * 50)
    print(f"Total documents: {total}")
    print(f"Documents with dates: {with_dates}")
    print(f"Documents with content: {with_content}")
    if date_range[0]:
        print(f"First download: {date_range[0]}")
        print(f"Last download: {date_range[1]}")
    
    conn.close()

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='View documents from database')
    parser.add_argument('--db', default='documents.db', help='Database file path')
    parser.add_argument('--limit', type=int, default=20, help='Number of documents to show')
    parser.add_argument('--search', help='Search term')
    parser.add_argument('--stats', action='store_true', help='Show statistics')
    
    args = parser.parse_args()
    
    if args.stats:
        get_statistics(args.db)
    else:
        view_documents(args.db, args.limit, args.search)

