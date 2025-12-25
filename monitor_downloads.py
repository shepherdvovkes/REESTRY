#!/usr/bin/env python3
"""
Monitor download progress
"""
import time
import sys
import os
import sqlite3
from datetime import datetime

def get_stats(db_path='documents.db'):
    """Get download statistics"""
    if not os.path.exists(db_path):
        return None
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM documents')
    total = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM documents WHERE date IS NOT NULL')
    with_dates = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM documents WHERE content IS NOT NULL AND content != ""')
    with_content = cursor.fetchone()[0]
    
    cursor.execute('SELECT MIN(downloaded_at), MAX(downloaded_at) FROM documents WHERE downloaded_at IS NOT NULL')
    date_range = cursor.fetchone()
    
    conn.close()
    
    return {
        'total': total,
        'with_dates': with_dates,
        'with_content': with_content,
        'date_range': date_range
    }

def main():
    interval = 10  # seconds
    if len(sys.argv) > 1:
        try:
            interval = int(sys.argv[1])
        except:
            pass
    
    print("Monitoring download progress... (Press Ctrl+C to stop)")
    print("=" * 60)
    
    try:
        while True:
            os.system('clear' if os.name != 'nt' else 'cls')
            
            print(f"\n📊 Download Progress Monitor - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 60)
            
            stats = get_stats()
            
            if stats is None:
                print("⏳ Database not created yet...")
            elif stats['total'] == 0:
                print("⏳ No documents downloaded yet...")
                print("   (Collection phase in progress)")
            else:
                print(f"✅ Total documents: {stats['total']:,}")
                print(f"   With dates: {stats['with_dates']:,}")
                print(f"   With content: {stats['with_content']:,}")
                
                if stats['date_range'][0]:
                    print(f"\n📅 First download: {stats['date_range'][0]}")
                    print(f"📅 Last download: {stats['date_range'][1]}")
                
                # Calculate rate if we have data
                if stats['date_range'][0] and stats['date_range'][1]:
                    try:
                        from datetime import datetime as dt
                        start = dt.fromisoformat(stats['date_range'][0].replace(' ', 'T'))
                        end = dt.fromisoformat(stats['date_range'][1].replace(' ', 'T'))
                        elapsed = (end - start).total_seconds()
                        if elapsed > 0:
                            rate = stats['total'] / elapsed * 60  # per minute
                            print(f"\n📈 Download rate: {rate:.2f} documents/minute")
                            
                            # Estimate time remaining
                            remaining = 262483 - stats['total']
                            if rate > 0:
                                minutes_remaining = remaining / rate
                                hours_remaining = minutes_remaining / 60
                                print(f"⏱️  Estimated time remaining: {hours_remaining:.1f} hours ({minutes_remaining:.0f} minutes)")
                    except:
                        pass
            
            print("\n" + "=" * 60)
            print(f"Refreshing every {interval} seconds... (Press Ctrl+C to stop)")
            
            time.sleep(interval)
    
    except KeyboardInterrupt:
        print("\n\n👋 Monitoring stopped")

if __name__ == '__main__':
    main()

