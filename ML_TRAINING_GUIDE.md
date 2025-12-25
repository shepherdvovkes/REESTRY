# ML Fine-Tuning Guide: Ukrainian Law Documents

## Best Strategy for Fine-Tuning Models

### Recommendation: **Hybrid Approach**

Download core dataset + Online access for updates

---

## Phase 1: Download Core Dataset (Recommended)

### Why Download?
- ✅ **Stable dataset** for reproducible training
- ✅ **Fast access** during training (no network latency)
- ✅ **No rate limits** during training iterations
- ✅ **Version control** - can track dataset versions
- ✅ **Offline training** possible

### What to Download?

#### 1. All Кодекси (Codes) - **HIGHEST PRIORITY**
These are foundational legal documents:
```bash
python3 download_strategy.py --codes
```

**Why**: Codes contain the most comprehensive legal knowledge and are referenced by all other documents.

#### 2. Top 1,000-10,000 Popular Documents
```bash
python3 download_strategy.py --top-popular 1000
```

**Why**: These cover the most common legal cases and questions.

#### 3. Recent Documents (Last 2 years)
For current legal practices and recent changes.

---

## Phase 2: Online Access for Updates

### When to Use Online Access:
- 🔄 Fetching newly published documents
- 🔍 On-demand queries for specific topics
- 📊 Keeping dataset current
- 🧪 Testing model on live data

### Implementation:
```python
from online_access import OnlineLawAPI

with OnlineLawAPI() as api:
    doc = api.get_document('2341-14')
    # Process document
```

---

## Dataset Size Estimates

Based on the [popular documents page](https://zakon.rada.gov.ua/laws/main/d):

| Dataset Size | Documents | Estimated Size | Use Case |
|-------------|-----------|----------------|----------|
| **Minimal** | ~50 codes | ~50-100 MB | Proof of concept |
| **Small** | Top 1,000 | ~500 MB - 1 GB | Domain adaptation |
| **Medium** | Top 10,000 | ~5-10 GB | Fine-tuning |
| **Large** | Top 100,000 | ~50-100 GB | Full fine-tuning |
| **Complete** | All 262,483 | ~250-500 GB | Comprehensive training |

---

## Recommended Workflow

### Step 1: Start Small (Proof of Concept)
```bash
# Download all codes
python3 download_strategy.py --codes

# Check what you have
python3 download_strategy.py --stats

# Export for training
python3 download_strategy.py --export training_data.txt
```

### Step 2: Scale Up Based on Results
```bash
# If results are good, download more
python3 download_strategy.py --top-popular 1000
python3 download_strategy.py --stats
python3 download_strategy.py --export training_data_large.txt
```

### Step 3: Ongoing Updates
- Use online API for new documents
- Periodically re-download popular documents to catch updates
- Monitor dataset statistics

---

## Data Quality Considerations

### Preprocessing for Training:
1. **Filter by content length**: Remove very short documents (< 1000 chars)
2. **Prioritize by type**: Codes > Laws > Decrees
3. **Clean text**: Remove UI elements, normalize whitespace
4. **Structure preservation**: Keep article numbers, sections

### Export Format:
```python
# Each document as:
=== Title ===
Type: Кодекс
Number: 2341-III

[Full content]

========================================
```

---

## Performance Tips

1. **Start with codes only** - test if approach works
2. **Incremental download** - add more documents as needed
3. **Use database** - SQLite for efficient querying
4. **Batch processing** - process documents in batches
5. **Monitor storage** - 262k documents = ~250-500 GB

---

## Cost-Benefit Analysis

### Download All (262,483 documents):
- **Time**: Days/weeks to download
- **Storage**: 250-500 GB
- **Pros**: Complete dataset, fast training
- **Cons**: Large storage, initial time investment

### Download Top 10,000:
- **Time**: Hours to download
- **Storage**: 5-10 GB
- **Pros**: Good coverage, manageable size
- **Cons**: Missing some documents

### Download Codes Only (~50):
- **Time**: Minutes
- **Storage**: 50-100 MB
- **Pros**: Fast, foundational knowledge
- **Cons**: Limited coverage

---

## Recommendation

**For initial fine-tuning**: Start with **all codes + top 1,000 popular documents**

This gives you:
- ✅ Foundational legal knowledge (codes)
- ✅ Common use cases (popular documents)
- ✅ Manageable dataset size (~1-2 GB)
- ✅ Fast to download and process

Then scale up based on model performance!

