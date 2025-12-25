# Ukraine Open Databases & Registries Web Application

A comprehensive web application that displays all open sources and registries from Ukraine, extracted from the problem.txt file.

## Features

- **226+ Ukrainian State Registries**: Complete directory of publicly accessible databases
- **Search & Filter**: Search by name, URL, or category
- **Sample Data**: Each registry displays sample data entries
- **Categories**: Organized into 10+ categories (Judiciary, Business, Property, Taxes, etc.)
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Direct Links**: Click through to access the actual registries

## Files

- `index.html` - Main web page
- `styles.css` - Styling and layout
- `app.js` - JavaScript functionality
- `sources_data.json` - Extracted registry data (generated)
- `parse_sources.py` - Parser script to extract data from problem.txt
- `problem.txt` - Source file with all registry information

## How to Use

### Option 1: Simple File Opening
1. Open `index.html` in a modern web browser
2. Note: Some browsers may block loading JSON files due to CORS. If this happens, use Option 2.

### Option 2: Local Server (Recommended)
1. Install Python 3 (if not already installed)
2. Run the local server:
   ```bash
   python3 -m http.server 8000
   ```
3. Open your browser and navigate to: `http://localhost:8000`

### Option 3: Using the Provided Server Script
```bash
python3 server.py
```
Then open `http://localhost:8000` in your browser.

## Regenerating Data

If you update `problem.txt`, regenerate the JSON data:
```bash
python3 parse_sources.py
```

## Categories

The registries are organized into the following categories:

- **Legislation & Norms** - Laws, codes, and legal documents
- **Judiciary & Enforcement** - Court decisions, enforcement proceedings
- **Business & Entities** - Company registries, business information
- **Property & Assets** - Real estate, land cadastre, property rights
- **Intellectual Property** - Patents, trademarks, IP rights
- **Finance & Taxes** - Tax registries, VAT payers, financial data
- **Anti-Corruption & Sanctions** - Corruption registries, sanctions lists
- **Health & Medicine** - Medical licenses, drug registries
- **Transport & Infrastructure** - Vehicle registration, transport licenses
- **Specialized** - Energy, environment, and other specialized registries

## Sample Data

Each registry entry includes:
- Sample data entries (2-3 examples)
- Total record count estimate
- Last updated date
- Direct link to view full data

## Browser Compatibility

- Chrome/Edge (recommended)
- Firefox
- Safari
- Opera

## Notes

- Sample data is generated based on registry type and is for demonstration purposes
- Actual data access may require registration or verification on some registries
- Some registries may be in test mode or have limited access due to security concerns
- URLs are extracted from the source file and should be verified for current accessibility

## License

This application is provided as-is for informational purposes. The data sources are publicly available Ukrainian government registries.

