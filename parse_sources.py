#!/usr/bin/env python3
"""
Parser script to extract registry information from problem.txt
"""
import re
import json

def parse_sources(file_path):
    """Parse problem.txt and extract registry names and URLs"""
    sources = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to match numbered entries: "1. Name - URL"
    pattern = r'^(\d+)\.\s+(.+?)\s+-\s+(https?://[^\s]+|N/A)'
    
    for line in content.split('\n'):
        match = re.match(pattern, line.strip())
        if match:
            number = match.group(1)
            name = match.group(2).strip()
            url = match.group(3).strip()
            
            # Skip entries with N/A URLs
            if url != 'N/A':
                sources.append({
                    'id': int(number),
                    'name': name,
                    'url': url,
                    'category': categorize_source(name)
                })
    
    # Also extract from the table format (lines 364-378)
    table_pattern = r'\|\s+([^|]+)\s+\|\s+(https?://[^\s]+)'
    table_matches = re.findall(table_pattern, content)
    for name, url in table_matches:
        name = name.strip()
        url = url.strip()
        if url and url != 'N/A' and not any(s['url'] == url for s in sources):
            sources.append({
                'id': len(sources) + 1,
                'name': name,
                'url': url,
                'category': categorize_source(name)
            })
    
    return sources

def categorize_source(name):
    """Categorize source based on name keywords"""
    name_lower = name.lower()
    
    if any(word in name_lower for word in ['суд', 'court', 'judicial', 'судовий']):
        return 'Judiciary & Enforcement'
    elif any(word in name_lower for word in ['закон', 'legislation', 'норматив', 'рада']):
        return 'Legislation & Norms'
    elif any(word in name_lower for word in ['підприємств', 'компані', 'бізнес', 'business', 'єдр']):
        return 'Business & Entities'
    elif any(word in name_lower for word in ['нерухом', 'property', 'майно', 'кадастр', 'земл']):
        return 'Property & Assets'
    elif any(word in name_lower for word in ['патент', 'торговельн', 'trademark', 'ip', 'інтелектуальн']):
        return 'Intellectual Property'
    elif any(word in name_lower for word in ['податк', 'tax', 'пдв', 'фінанс']):
        return 'Finance & Taxes'
    elif any(word in name_lower for word in ['корупц', 'санкц', 'corruption', 'sanction']):
        return 'Anti-Corruption & Sanctions'
    elif any(word in name_lower for word in ['медичн', 'лікар', 'health', 'медицина']):
        return 'Health & Medicine'
    elif any(word in name_lower for word in ['транспорт', 'transport', 'авто', 'vehicle']):
        return 'Transport & Infrastructure'
    elif any(word in name_lower for word in ['енерг', 'energy', 'монопол']):
        return 'Specialized (Energy, Environment)'
    else:
        return 'Other'

def generate_sample_data(name, url):
    """Generate sample data based on registry type"""
    name_lower = name.lower()
    
    if 'суд' in name_lower or 'court' in name_lower or 'судовий' in name_lower:
        return {
            'sample': [
                {'case_number': '123/456/2024', 'date': '2024-01-15', 'court': 'Kyiv City Court', 'summary': 'Commercial dispute resolution'},
                {'case_number': '789/012/2024', 'date': '2024-02-20', 'court': 'Lviv Regional Court', 'summary': 'Property rights case'}
            ],
            'total_records': '2,450,000+',
            'last_updated': '2024-12-15'
        }
    elif 'підприємств' in name_lower or 'єдр' in name_lower or 'business' in name_lower or 'компані' in name_lower:
        return {
            'sample': [
                {'code': '12345678', 'name': 'ТОВ "Приклад"', 'status': 'Active', 'registration_date': '2020-05-10'},
                {'code': '87654321', 'name': 'ФОП Іванов І.І.', 'status': 'Active', 'registration_date': '2019-03-22'}
            ],
            'total_records': '1,850,000+',
            'last_updated': '2024-12-20'
        }
    elif 'нерухом' in name_lower or 'property' in name_lower or 'майно' in name_lower or 'кадастр' in name_lower:
        return {
            'sample': [
                {'property_id': 'UA-12345', 'address': 'Kyiv, Shevchenko Ave. 1', 'owner': 'Private', 'area': '120 sq.m'},
                {'property_id': 'UA-67890', 'address': 'Lviv, Freedom Ave. 5', 'owner': 'Private', 'area': '85 sq.m'}
            ],
            'total_records': '15,000,000+',
            'last_updated': '2024-12-18'
        }
    elif 'податк' in name_lower or 'tax' in name_lower or 'пдв' in name_lower:
        return {
            'sample': [
                {'taxpayer_id': '1234567890', 'name': 'ТОВ "Приклад"', 'vat_status': 'Active', 'registration_date': '2020-01-15'},
                {'taxpayer_id': '0987654321', 'name': 'ФОП Петров П.П.', 'vat_status': 'Active', 'registration_date': '2018-06-20'}
            ],
            'total_records': '3,200,000+',
            'last_updated': '2024-12-19'
        }
    elif 'патент' in name_lower or 'trademark' in name_lower or 'торговельн' in name_lower or 'інтелектуальн' in name_lower:
        return {
            'sample': [
                {'application_number': 'U 2024 00001', 'title': 'Software System', 'applicant': 'ТОВ "Технології"', 'status': 'Pending'},
                {'application_number': 'U 2024 00002', 'title': 'Trademark "Example"', 'applicant': 'ФОП Іванов', 'status': 'Registered'}
            ],
            'total_records': '450,000+',
            'last_updated': '2024-12-17'
        }
    elif 'закон' in name_lower or 'legislation' in name_lower or 'норматив' in name_lower or 'рада' in name_lower:
        return {
            'sample': [
                {'law_number': '1234-VIII', 'title': 'Про захист прав споживачів', 'date': '2024-01-10', 'status': 'Active'},
                {'law_number': '5678-IX', 'title': 'Про цифрові послуги', 'date': '2024-02-15', 'status': 'Active'}
            ],
            'total_records': '25,000+',
            'last_updated': '2024-12-20'
        }
    elif 'боржник' in name_lower or 'debtor' in name_lower or 'виконавч' in name_lower:
        return {
            'sample': [
                {'debtor_name': 'ТОВ "Приклад"', 'debt_amount': '125,000 UAH', 'creditor': 'State Tax Service', 'status': 'Active'},
                {'debtor_name': 'ФОП Іванов', 'debt_amount': '45,000 UAH', 'creditor': 'Bank', 'status': 'Active'}
            ],
            'total_records': '850,000+',
            'last_updated': '2024-12-19'
        }
    elif 'корупц' in name_lower or 'corruption' in name_lower or 'санкц' in name_lower or 'sanction' in name_lower:
        return {
            'sample': [
                {'person_name': 'Іванов І.І.', 'position': 'Public Official', 'violation_date': '2023-05-10', 'status': 'Under investigation'},
                {'person_name': 'Петров П.П.', 'position': 'Former Official', 'violation_date': '2022-11-20', 'status': 'Convicted'}
            ],
            'total_records': '15,000+',
            'last_updated': '2024-12-18'
        }
    elif 'медичн' in name_lower or 'лікар' in name_lower or 'health' in name_lower:
        return {
            'sample': [
                {'license_number': 'MD-12345', 'name': 'Dr. Іванов І.І.', 'specialization': 'Cardiology', 'status': 'Active'},
                {'license_number': 'MD-67890', 'name': 'Dr. Петрова П.П.', 'specialization': 'Pediatrics', 'status': 'Active'}
            ],
            'total_records': '250,000+',
            'last_updated': '2024-12-17'
        }
    elif 'транспорт' in name_lower or 'transport' in name_lower or 'авто' in name_lower or 'vehicle' in name_lower:
        return {
            'sample': [
                {'vehicle_number': 'AA1234BB', 'owner': 'Іванов І.І.', 'make': 'Toyota', 'year': '2020', 'status': 'Registered'},
                {'vehicle_number': 'BC5678AA', 'owner': 'ТОВ "Приклад"', 'make': 'Volkswagen', 'year': '2019', 'status': 'Registered'}
            ],
            'total_records': '8,500,000+',
            'last_updated': '2024-12-20'
        }
    elif 'ліценз' in name_lower or 'license' in name_lower:
        return {
            'sample': [
                {'license_number': 'LIC-12345', 'holder': 'ТОВ "Приклад"', 'activity': 'Retail Trade', 'expiry': '2025-12-31', 'status': 'Active'},
                {'license_number': 'LIC-67890', 'holder': 'ФОП Іванов', 'activity': 'Construction', 'expiry': '2026-06-30', 'status': 'Active'}
            ],
            'total_records': '450,000+',
            'last_updated': '2024-12-19'
        }
    elif 'нотар' in name_lower or 'notary' in name_lower:
        return {
            'sample': [
                {'notary_name': 'Іванов І.І.', 'district': 'Kyiv', 'certificate_number': 'NOT-12345', 'status': 'Active'},
                {'notary_name': 'Петрова П.П.', 'district': 'Lviv', 'certificate_number': 'NOT-67890', 'status': 'Active'}
            ],
            'total_records': '8,500+',
            'last_updated': '2024-12-18'
        }
    elif 'банкрут' in name_lower or 'bankruptcy' in name_lower:
        return {
            'sample': [
                {'company_name': 'ТОВ "Приклад"', 'case_number': 'B-123/2024', 'status': 'In process', 'date': '2024-01-15'},
                {'company_name': 'ТОВ "Приклад2"', 'case_number': 'B-456/2024', 'status': 'Completed', 'date': '2024-02-20'}
            ],
            'total_records': '45,000+',
            'last_updated': '2024-12-17'
        }
    else:
        return {
            'sample': [
                {'id': '001', 'name': 'Sample Record 1', 'status': 'Active', 'date': '2024-01-10'},
                {'id': '002', 'name': 'Sample Record 2', 'status': 'Active', 'date': '2024-02-15'}
            ],
            'total_records': '10,000+',
            'last_updated': '2024-12-15'
        }

if __name__ == '__main__':
    sources = parse_sources('problem.txt')
    
    # Add sample data to each source
    for source in sources:
        source['sample_data'] = generate_sample_data(source['name'], source['url'])
    
    # Save as JSON
    with open('sources_data.json', 'w', encoding='utf-8') as f:
        json.dump(sources, f, ensure_ascii=False, indent=2)
    
    print(f"Extracted {len(sources)} sources")
    print(f"Saved to sources_data.json")

