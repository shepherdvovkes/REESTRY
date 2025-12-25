#!/usr/bin/env python3
"""
Пример использования UkrDeepCrawler
"""
from crawler import LLMCrawler

def main():
    # Инициализация crawler
    # Можно указать свой LMStudio URL или использовать из config.py
    crawler = LLMCrawler(
        lmstudio_url="http://192.168.0.60:1234/v1/chat/completions"
    )
    
    # Seed URLs - начальные точки обхода
    seed_urls = [
        "https://data.gov.ua",  # Национальный портал открытых данных
        "https://usr.minjust.gov.ua",  # Единый государственный реестр
        "https://opendatabot.ua",  # Агрегатор открытых данных
        "https://nazk.gov.ua",  # НАЗК - антикоррупционное агентство
        "https://minjust.gov.ua/m/edini-ta-derjavni-reestri"  # Список реестров Минюста
    ]
    
    print("="*60)
    print("🇺🇦 UkrDeepCrawler - Поиск источников открытых данных")
    print("="*60)
    print()
    
    # Запуск обхода
    crawler.crawl(
        seed_urls=seed_urls,
        max_depth=4,      # Максимальная глубина обхода
        max_pages=500     # Максимальное количество страниц
    )
    
    # Сохранение результатов
    crawler.save_results("ukrainian_registries_crawl.json")
    
    print("\n✅ Готово! Результаты сохранены в ukrainian_registries_crawl.json")
    print("\nНайденные релевантные URL:")
    for i, url_info in enumerate(crawler.relevant_urls[:10], 1):
        print(f"  {i}. [{url_info['type']}] {url_info['url']} (relevance: {url_info['relevance']}/10)")


if __name__ == "__main__":
    main()

