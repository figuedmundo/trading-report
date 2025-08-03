import logging
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from typing import List, Dict, Any
from datetime import datetime


logger = logging.getLogger(__name__)

class ContentExtractor:
    def extract_urls_from_email(self, email_content: str) -> List[str]:
        """Extract URLs from email HTML content that match specific domain and path"""
        soup = BeautifulSoup(email_content, "html.parser")
        urls = []

        for link in soup.find_all("a", href=True):
            href = link["href"]
            parsed = urlparse(href)

            # Only allow links from protradingskills.com with path starting with /analysis
            if parsed.netloc.lower() == "protradingskills.com" and parsed.path.startswith("/analysis"):
                urls.append(href)

        logger.info(f"Extracted urls: {len(urls)}")
        return urls
    

    def create_summary_structure(self, scraped_report: str, ai_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Create a structured summary combining extracted content and AI analysis"""
        cleaned_content = self.clean_html_content(scraped_report)
        
        return {
            'metadata': {
                'title': cleaned_content['title'],
                'word_count': cleaned_content['word_count'],
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')  
            },
            'content': {
                'original_text': cleaned_content['main_content'],
                'translated_content': ai_analysis.get('translated_content', ''),
                'original_html': scraped_report.get('html_content', ''),
                'report_images': scraped_report.get('report_images')
            },
            'analysis': {
                'summary': ai_analysis.get('summary', ''),
                'key_insights': ai_analysis.get('key_insights', []),
                'market_metrics': ai_analysis.get('market_metrics', {}),
                'outlook': ai_analysis.get('outlook', ''),
                'risk_factors': ai_analysis.get('risk_factors', []),
                'action_items': ai_analysis.get('action_items', []),
                'confidence_level': ai_analysis.get('confidence_level', '')
            }
        }
    
    def clean_html_content(self, report: dict) -> dict:
        """Clean HTML content and prepare structured data from the scraped report"""

        title = report.get("title") or ""
        html_content = report.get("html_content") or ""
        
        # Strip HTML tags
        soup = BeautifulSoup(html_content, "html.parser")
        text = soup.get_text(separator="\n", strip=True)

        return {
            "title": title.strip(),
            "main_content": text,
            "word_count": len(text.split())
        }