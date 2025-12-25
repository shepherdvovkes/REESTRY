# Document Downloader for zakon.rada.gov.ua

This application downloads all popular documents from the Verkhovna Rada (Parliament) of Ukraine website and stores them in a SQLite database.

## Installation

1. Install required Python packages:
```bash
pip3 install -r requirements.txt
```

Or install individually:
```bash
pip3 install requests beautifulsoup4 lxml
```

## Rate Limiting & Restrictions

Based on [zakon.rada.gov.ua policies](https://people.rada.gov.ua/body/main/en/rules):

- **Limit on pages per minute** from single IP address
- **Excessive requests** = temporary denial (several minutes)
- **Repeated violations** = 24 hour or permanent suspension
- **Peak hours** (10:00-13:00, 14:00-17:00) may timeout after 10 seconds

### Recommended Settings

- **Workers**: 3-5 concurrent threads (higher may trigger rate limits)
- **Requests per minute**: 
  - Conservative: 20-30 req/min (safer, slower)
  - Moderate: 30-40 req/min (balanced)
  - Aggressive: 40+ req/min (risky, may cause bans)

## Usage

### Basic Usage

**Test mode** (downloads 10 documents to test):
```bash
python3 download_documents.py --test
```

**Download all documents** (default: 3 workers, 30 req/min):
```bash
python3 download_documents.py
```

**Download with custom settings**:
```bash
python3 download_documents.py --max 1000 --workers 5 --requests-per-minute 40
```

**Verbose output** (detailed logging):
```bash
python3 download_documents.py --verbose
```

### Command Line Options

- `--max N` - Maximum number of documents to download
- `--workers N` - Number of concurrent workers (default: 3, recommended: 3-5)
- `--requests-per-minute N` - Maximum requests per minute (default: 30, recommended: 20-40)
- `--db PATH` - Database file path (default: documents.db)
- `--test` - Test mode: download only 10 documents
- `--verbose, -v` - Verbose output with detailed logging

### Examples

```bash
# Download first 100 documents
python3 download_documents.py --max 100

# Download with 2 second delay (be respectful to server)
python3 download_documents.py --delay 2.0

# Use custom database name
python3 download_documents.py --db my_documents.db
```

## Viewing Downloaded Documents

### View recent documents:
```bash
python3 view_documents.py
```

### View with search:
```bash
python3 view_documents.py --search "кодекс"
```

### View statistics:
```bash
python3 view_documents.py --stats
```

### View more documents:
```bash
python3 view_documents.py --limit 50
```

## Database Schema

The SQLite database contains the following table:

```sql
CREATE TABLE documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT UNIQUE,        -- Extracted from URL (e.g., "2341-14")
    title TEXT,                      -- Document title
    document_type TEXT,              -- Type of document
    document_number TEXT,             -- Document number (e.g., "2341-III")
    date TEXT,                        -- Document date
    status TEXT,                      -- Document status
    url TEXT,                         -- Full URL to document
    content TEXT,                     -- Document content (first 50KB)
    metadata TEXT,                    -- JSON metadata
    downloaded_at TIMESTAMP,         -- When document was downloaded
    updated_at TIMESTAMP             -- Last update time
);
```

## Important Notes

1. **Rate Limiting**: 
   - Default: 3 workers, 30 requests/minute
   - For 262,483 documents: ~146 hours (6 days) at 30 req/min
   - The script automatically calculates and displays optimal parameters
   - Progress is reported every 30 seconds with detailed statistics
   - Rate limit violations are automatically detected and handled

2. **Multi-threading**: 
   - Uses ThreadPoolExecutor for concurrent downloads
   - Thread-safe database operations
   - Automatic rate limiting across all threads
   - Connection pooling for efficiency

2. **Website Structure**: The website structure may change. If the downloader stops working:
   - Check if the website structure has changed
   - The parser may need to be updated to match new HTML structure
   - Some documents may require authentication or have different access patterns

3. **Resume Capability**: The script automatically skips documents that are already in the database, so you can:
   - Stop and restart the script safely
   - Run it multiple times to catch new documents
   - Resume interrupted downloads

4. **Content Size**: Document content is limited to 50KB to keep database size manageable. Full content can be accessed via the URL.

5. **Error Handling**: The script includes error handling and will continue even if some documents fail to download.

## Verbose Output

The `--verbose` flag provides detailed logging:

- **DEBUG level**: Every request, rate limit waits, parsing details
- **INFO level**: Document downloads, saves, progress updates
- **WARNING level**: Rate limit hits, errors, retries
- **Progress reports**: Every 30 seconds with full statistics

Example verbose output:
```
2024-12-25 10:30:15 [INFO] ⬇️  Downloading: Кримінальний кодекс України...
2024-12-25 10:30:16 [DEBUG] 🌐 Fetching document (Rate: 15/30/min)
2024-12-25 10:30:17 [INFO] ✅ Saved: 2341-14
2024-12-25 10:30:45 [INFO] ================================================================================
2024-12-25 10:30:45 [INFO] 📊 PROGRESS STATISTICS
2024-12-25 10:30:45 [INFO]    ✅ Downloaded: 45
2024-12-25 10:30:45 [INFO]    ⏭️  Skipped: 12
2024-12-25 10:30:45 [INFO]    ❌ Errors: 2
2024-12-25 10:30:45 [INFO]    🌐 Total Requests: 59
2024-12-25 10:30:45 [INFO]    ⚠️  Rate Limit Hits: 0
2024-12-25 10:30:45 [INFO]    ⏱️  Elapsed Time: 2.5 minutes
2024-12-25 10:30:45 [INFO]    📈 Request Rate: 0.39 req/sec
2024-12-25 10:30:45 [INFO]    📈 Download Rate: 0.30 docs/sec
2024-12-25 10:30:45 [INFO]    📊 Current Rate Limit: 18/30 req/min
```

## Troubleshooting

### Rate limit errors (429)
- Reduce `--requests-per-minute` (try 20-25)
- Reduce `--workers` (try 2-3)
- Wait a few minutes and resume
- The script automatically handles rate limits with exponential backoff

### Connection errors
- Check your internet connection
- The website may be temporarily unavailable
- Peak hours (10:00-13:00, 14:00-17:00) may be slower
- Try reducing concurrency: `--workers 2`

### No documents found
- The website structure may have changed
- Check if the popular documents page is accessible
- Use `--verbose` to see what's being fetched
- You may need to update the parsing logic

### Database locked
- Make sure only one instance of the downloader is running
- Close any database viewers that might have the database open
- SQLite handles concurrent reads, but only one write at a time

### High error rate
- Check verbose output for specific error messages
- May indicate rate limiting - reduce `--requests-per-minute`
- May indicate website changes - check if site is accessible

## Performance Tips

For downloading all 262,483 documents:

1. **Start with test mode** to verify everything works:
   ```bash
   python3 download_documents.py --test --verbose
   ```

2. **Use conservative settings** initially:
   ```bash
   python3 download_documents.py --workers 3 --requests-per-minute 25
   ```

3. **Monitor verbose output** to see rate limiting in action:
   ```bash
   python3 download_documents.py --verbose
   ```

4. **Use screen/tmux** for long-running sessions:
   ```bash
   screen -S downloader
   python3 download_documents.py --workers 4 --requests-per-minute 30
   # Press Ctrl+A then D to detach
   ```

5. **Monitor progress** (reports every 30 seconds automatically):
   - Progress statistics are printed every 30 seconds
   - Shows: downloaded, skipped, errors, rate, elapsed time
   - Use `--verbose` for per-document logging

6. **Resume capability**: The script automatically skips already downloaded documents, so you can:
   - Stop and restart safely
   - Run multiple times to catch new documents
   - Resume interrupted downloads

## Legal and Ethical Considerations

- This tool is for educational and research purposes
- Respect the website's robots.txt and terms of service
- Use appropriate delays to avoid overloading the server
- The documents are publicly available, but be mindful of server resources
- Consider contacting the website administrators if you plan large-scale downloads

## References

- [Verkhovna Rada Legislation Portal](https://zakon.rada.gov.ua)
- [Help Page](https://zakon.rada.gov.ua/laws/main/help#Zapyt)

