from urllib.parse import urlparse
from readability import Document # type: ignore
from bs4 import BeautifulSoup
import requests
from urllib.robotparser import RobotFileParser
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed
from app.core.config import settings

class URLProcessor:
    def __init__(self):
        self.session = requests.Session()  # Reuse session
        self.session.headers.update({'User-Agent': settings.SCRAPER_USER_AGENT})

    def _get_domain(self, url):
        # Helper to extract domain safely
        try:
            return urlparse(url).netloc
        except Exception:
            raise ValueError("Invalid URL format")

    def _check_robots(self, url):
        # Check if scraping is allowed by robots.txt
        domain = self._get_domain(url)
        robots_url = f"http://{domain}/robots.txt"
        rp = RobotFileParser()
        rp.set_url(robots_url)
        try:
            rp.read()
            return rp.can_fetch('*', url)
        except Exception as e:
            raise ValueError(f"Error reading robots.txt: {str(e)}")

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2), retry=retry_if_exception_type(requests.RequestException))
    def fetch_url(self, url):
            domain = self._get_domain(url)
            if not self._check_robots(url):
                raise ValueError(f"Scraping disallowed by robots.txt for {domain}")
            
            response = self.session.get(url, timeout=(3.05, 27))
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            main_content = self._extract_main_content(soup)
            
            if not main_content:
                raise ValueError("No extractable content found")
            
            return self._clean_content(main_content)
        
    def _extract_main_content(self, soup):
        # Extract main content using readability-lxml
        doc = Document(str(soup))
        return doc.summary()

    def _clean_content(self, html_content):
        # Clean extracted HTML content
        soup = BeautifulSoup(html_content, 'html.parser')
        return soup.get_text(separator='\n', strip=True)