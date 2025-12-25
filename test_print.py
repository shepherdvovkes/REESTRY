#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup

url = 'https://zakon.rada.gov.ua/laws/show/2341-14/print'
r = requests.get(url, timeout=30, headers={'User-Agent': 'Mozilla/5.0'})
print(f'Status: {r.status_code}')
print(f'Content length: {len(r.text):,} chars')
soup = BeautifulSoup(r.text, 'html.parser')
body = soup.find('body')
if body:
    text = body.get_text(separator=' ', strip=True)
    print(f'Body text length: {len(text):,} chars')
    print(f'\nFirst 1000 chars:')
    print('='*60)
    print(text[:1000])
    print('='*60)

