#!/usr/bin/env python3
"""
Online API access for Ukrainian law documents
Use this for:
- Fetching specific documents on-demand
- Getting latest updates
- Querying without downloading everything
"""
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re
import json

class OnlineLawAPI:
    def __init__(self):
        self.base_url = 'https://zakon.rada.gov.ua'
        self.playwright = None
        self.browser = None
        self.page = None
    
    def __enter__(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)
        self.page = self.browser.new_page()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
    
    def get_document(self, document_id):
        """Get a specific document by ID"""
        url = f"{self.base_url}/laws/show/{document_id}/print"
        self.page.goto(url, wait_until='networkidle', timeout=60000)
        self.page.wait_for_timeout(2000)
        
        html = self.page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract content (simplified - use full extraction from extract_with_playwright)
        body = soup.find('body')
        if body:
            for element in body.find_all(['script', 'style', 'nav', 'header', 'footer']):
                element.decompose()
            text = body.get_text(separator='\n', strip=True)
            return text
        return None
    
    def search_documents(self, query, max_results=10):
        """Search for documents (if search API exists)"""
        # Implementation would depend on available search endpoints
        pass
    
    def get_recent_documents(self, days=30):
        """Get recently published documents"""
        # Implementation would fetch from recent documents page
        pass

# Example usage:
if __name__ == '__main__':
    # Use as context manager for automatic cleanup
    with OnlineLawAPI() as api:
        doc = api.get_document('2341-14')
        if doc:
            print(f"Document length: {len(doc):,} characters")
            print(f"Preview: {doc[:500]}")

