import logging
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from typing import List

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