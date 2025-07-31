from bs4 import BeautifulSoup
import re

def extract_url_from_email(body):
    soup = BeautifulSoup(body, 'html.parser')
    for a in soup.find_all('a', href=True):
        if any(k in a['href'].lower() for k in ['report', 'market', 'analysis']):
            return a['href']
    urls = re.findall(r'https?://[^\s<>"\']+', body)
    return urls[0] if urls else None

def extract_main_content(html):
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup(['script', 'style', 'header', 'footer', 'aside']):
        tag.decompose()
    content = soup.select_one('main') or soup.select_one('article')
    if content:
        return content.get_text(strip=True)
    return soup.get_text(separator=' ', strip=True)
