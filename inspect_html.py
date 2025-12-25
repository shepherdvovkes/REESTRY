#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import re

url = 'https://zakon.rada.gov.ua/laws/show/2341-14/print'
r = requests.get(url, timeout=30, headers={'User-Agent': 'Mozilla/5.0'})
soup = BeautifulSoup(r.text, 'html.parser')
body = soup.find('body')

# Remove UI elements
for element in body.find_all(['script', 'style', 'nav', 'header', 'footer', 'button', 'form', 'link', 'meta']):
    element.decompose()

# Get all text
all_text = body.get_text(separator='\n', strip=True)
lines = all_text.split('\n')

print(f"Total lines: {len(lines)}")
print(f"Non-empty lines: {len([l for l in lines if l.strip()])}")

# Check first 50 lines
print("\nFirst 50 lines:")
for i, line in enumerate(lines[:50]):
    stripped = line.strip()
    if stripped:
        print(f"{i:3d}: {stripped[:100]}")

# Test current filtering
print("\n\nTesting current filter:")
filtered = []
for line in lines:
    stripped = line.strip()
    if stripped and len(stripped) > 0:
        ui_keywords = ['Друкувати', 'Допомога', 'Шрифт:', 'mouse wheel', 'Ctrl +']
        if not any(keyword in stripped for keyword in ui_keywords):
            filtered.append(line)

print(f"After filtering: {len(filtered)} lines")
print(f"First 10 filtered lines:")
for i, line in enumerate(filtered[:10]):
    print(f"{i}: {line[:100]}")

