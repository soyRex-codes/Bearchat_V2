"""
Production MSU Data Scraper (2025)
==================================
Modern web scraper using industry-standard tools for LLM training data.

Tech Stack:
- trafilatura: Professional-grade content extraction (used by Common Crawl)
- httpx: Modern async HTTP client
- JSON-LD: Structured data extraction
- Smart caching & rate limiting

Install dependencies:
    pip install trafilatura httpx

Usage:
    python web_scrapping_script.py

Features:
✓ Automatic content extraction (no manual parsing)
✓ JSON-LD structured data support
✓ Async batch processing
✓ Smart caching (avoid re-scraping)
✓ Rate limiting (respectful)
✓ High-quality Q&A generation
✓ Direct output to training format
"""

import json
import re
import asyncio
import hashlib
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from urllib.parse import urlparse

try:
    import httpx
    from trafilatura import extract
    from trafilatura.settings import use_config
except ImportError:
    print("❌ Missing dependencies!")
    print("Install with: pip install trafilatura httpx playwright")
    print("Then run: playwright install chromium")
    exit(1)

# Try to import Playwright (for JavaScript sites)
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️  Playwright not installed - will use basic HTTP (may fail on modern sites)")
    print("For better results: pip install playwright && playwright install chromium")



class MSUDataScraper:
    """Production-grade scraper for MSU content."""
    
    def __init__(self, cache_dir: str = ".scrape_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # Configure trafilatura for better extraction
        self.config = use_config()
        self.config.set("DEFAULT", "EXTRACTION_TIMEOUT", "30")
        
    def _cache_key(self, url: str) -> str:
        """Generate cache filename from URL."""
        return hashlib.md5(url.encode()).hexdigest()
    
    def _load_cache(self, url: str) -> Optional[Dict]:
        """Load cached content."""
        cache_file = self.cache_dir / f"{self._cache_key(url)}.json"
        if cache_file.exists():
            try:
                with open(cache_file) as f:
                    data = json.load(f)
                    # Check if cache is less than 7 days old
                    cache_date = datetime.fromisoformat(data.get('cached_at', ''))
                    if (datetime.now() - cache_date).days < 7:
                        return data
            except:
                pass
        return None
    
    def _save_cache(self, url: str, data: Dict):
        """Save content to cache."""
        cache_file = self.cache_dir / f"{self._cache_key(url)}.json"
        data['cached_at'] = datetime.now().isoformat()
        with open(cache_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    async def fetch_content(self, url: str) -> Optional[str]:
        """Fetch URL content - uses Playwright for JavaScript sites."""
        
        # Try Playwright first (handles JavaScript)
        if PLAYWRIGHT_AVAILABLE:
            try:
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    page = await browser.new_page()
                    
                    # Set longer timeout for slow-loading pages
                    page.set_default_timeout(60000)  # 60 seconds
                    
                    # Navigate and wait for content to load
                    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    
                    # Wait for any dynamic content to finish loading
                    await page.wait_for_timeout(3000)
                    
                    # Get final HTML after JavaScript execution
                    html = await page.content()
                    await browser.close()
                    
                    return html
            except Exception as e:
                print(f"  ⚠️  Playwright failed: {e}")
                print(f"  Falling back to basic HTTP...")
        
        # Fallback to basic HTTP
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    url,
                    headers={'User-Agent': 'Mozilla/5.0 (Educational Research Bot)'},
                    follow_redirects=True
                )
                response.raise_for_status()
                return response.text
        except Exception as e:
            print(f"  ✗ Fetch error: {e}")
            return None
    
    def extract_json_ld(self, html: str) -> List[Dict]:
        """Extract JSON-LD structured data from HTML."""
        pattern = r'<script type="application/ld\+json">(.*?)</script>'
        matches = re.findall(pattern, html, re.DOTALL)
        
        structured_data = []
        for match in matches:
            try:
                data = json.loads(match)
                structured_data.append(data)
            except json.JSONDecodeError:
                continue
        
        return structured_data
    
    def extract_main_content(self, html: str, url: str) -> Optional[Dict]:
        """
        Extract main content using trafilatura (industry standard).
        
        Trafilatura automatically:
        - Removes navigation, ads, footers
        - Extracts main article text
        - Preserves structure (headings, lists)
        - Cleans formatting
        """
        # Extract with trafilatura (handles all the messy parsing)
        content = extract(
            html,
            include_tables=True,
            include_links=True,
            include_images=False,
            output_format='json',
            config=self.config,
            favor_precision=False,  # Get more content even if less precise
            favor_recall=True  # Prioritize getting all content
        )
        
        if not content:
            return None
        
        # Parse JSON output
        try:
            data = json.loads(content)
            
            # If title is missing, extract from HTML manually
            title = data.get('title', '').strip()
            if not title or len(title) < 3:
                # Try to extract from <title> tag or <h1>
                import re
                title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
                if title_match:
                    title = title_match.group(1).strip()
                    # Clean up common suffixes
                    title = re.sub(r'\s*[\|\-]\s*Missouri State.*$', '', title, flags=re.IGNORECASE)
                    title = re.sub(r'\s*[\|\-]\s*MSU.*$', '', title, flags=re.IGNORECASE)
                
                # If still no title, try <h1>
                if not title or len(title) < 3:
                    h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.IGNORECASE | re.DOTALL)
                    if h1_match:
                        # Remove HTML tags from h1 content
                        title = re.sub(r'<[^>]+>', '', h1_match.group(1)).strip()
            
            # Get text - if too short, try extracting more aggressively
            text = data.get('text', '').strip()
            
            if len(text) < 500:
                # Trafilatura didn't get enough content
                # Try extracting from <main>, <article>, or <div class="content">
                import re
                from bs4 import BeautifulSoup
                
                soup = BeautifulSoup(html, 'html.parser')
                
                # Remove unwanted elements
                for elem in soup.find_all(['script', 'style', 'nav', 'footer', 'aside', 'header']):
                    elem.decompose()
                
                # Try to find main content area
                main_content = (
                    soup.find('main') or
                    soup.find('article') or 
                    soup.find(class_=lambda x: x and 'content' in x.lower()) or
                    soup.find(id=lambda x: x and 'content' in x.lower()) or
                    soup.find('body')
                )
                
                if main_content:
                    # Get all text from paragraphs and headings
                    paragraphs = main_content.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'li'])
                    extracted_text = []
                    
                    for p in paragraphs:
                        p_text = p.get_text(strip=True)
                        if len(p_text) > 20:  # Skip very short fragments
                            extracted_text.append(p_text)
                    
                    if extracted_text:
                        text = '\n\n'.join(extracted_text)
            
            return {
                'title': title or 'Missouri State Information',
                'author': data.get('author', ''),
                'date': data.get('date', ''),
                'text': text,
                'raw_text': data.get('raw_text', ''),
                'comments': data.get('comments', ''),
                'url': url
            }
        except Exception as e:
            print(f"  ✗ Parse error: {e}")
            return None
    
    def detect_content_type(self, title: str, url: str, text: str) -> str:
        """Detect content category."""
        combined = f"{title} {url}".lower()
        
        if any(word in combined for word in ['degree', 'program', 'major', 'bachelor', 'master']):
            return 'academic_program'
        elif any(word in combined for word in ['scholarship', 'financial', 'tuition', 'aid']):
            return 'financial_aid'
        elif any(word in combined for word in ['admission', 'apply', 'application', 'requirements']):
            return 'admissions'
        elif any(word in combined for word in ['housing', 'residence', 'dorm']):
            return 'housing'
        elif any(word in combined for word in ['course', 'curriculum', 'syllabus']):
            return 'academics'
        else:
            return 'general_info'
    
    def generate_training_data(self, content: Dict, content_type: str) -> List[Dict]:
        """
        Generate high-quality Q&A pairs for training.
        
        Strategy:
        - Overview questions (broad understanding)
        - Specific detail questions
        - Comparison questions
        - Practical application questions
        """
        training_data = []
        title = content.get('title', 'MSU Information')
        text = content.get('text', '')
        url = content.get('url', '')
        
        if not text or len(text) < 100:
            return []
        
        # Split text into chunks for different types of questions
        paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 50]
        
        # Metadata template
        def make_entry(instruction: str, response: str, context: str = "general"):
            return {
                "instruction": instruction,
                "response": response,
                "metadata": {
                    "topic": title,
                    "source_url": url,
                    "content_type": content_type,
                    "context_type": context,
                    "collected_date": datetime.now().strftime("%Y-%m-%d")
                }
            }
        
        # 1. Overview question
        if paragraphs:
            overview = ' '.join(paragraphs[:3])
            overview = self.truncate_at_sentence(overview, 1200)  # Smart truncation
            training_data.append(make_entry(
                f"Tell me about {title}.",
                overview,
                "overview"
            ))
            
            training_data.append(make_entry(
                f"What is {title}?",
                overview,
                "overview"
            ))
        
        # 2. Detailed questions from specific paragraphs
        for i, para in enumerate(paragraphs[:5]):
            if len(para) > 100:
                # Extract key topic from paragraph
                words = para.split()[:10]
                key_phrase = ' '.join(words[:5])
                
                if content_type == 'academic_program':
                    questions = [
                        f"What are the details about {title}?",
                        f"Tell me more about the {title} program.",
                        f"What should I know about {title}?",
                    ]
                elif content_type == 'admissions':
                    questions = [
                        f"How do I apply to {title}?",
                        f"What are the requirements for {title}?",
                        f"Tell me about the {title} process.",
                    ]
                elif content_type == 'financial_aid':
                    questions = [
                        f"How does {title} work?",
                        f"What financial aid options are available?",
                        f"Tell me about {title}.",
                    ]
                else:
                    questions = [
                        f"What information is available about {title}?",
                        f"Can you explain {title}?",
                    ]
                
                if i < len(questions):
                    training_data.append(make_entry(
                        questions[i],
                        self.truncate_at_sentence(para, 1000),  # Smart truncation
                        "specific_detail"
                    ))
        
        # 3. Full content question (for comprehensive info)
        if len(text) > 200:
            full_text = self.truncate_at_sentence(text, 2500)  # Smart truncation
            training_data.append(make_entry(
                f"Give me comprehensive information about {title}.",
                full_text,
                "comprehensive"
            ))
        
        # 4. Reference question
        training_data.append(make_entry(
            f"Where can I learn more about {title}?",
            f"You can find detailed information at: {url}",
            "reference"
        ))
        
        return training_data
    
    def truncate_at_sentence(self, text: str, max_chars: int) -> str:
        """
        Truncate text at the last complete sentence before max_chars.
        Avoids mid-sentence cutoffs for better training data quality.
        """
        if len(text) <= max_chars:
            return text
        
        # Find the last sentence boundary (., !, ?) before max_chars
        truncated = text[:max_chars]
        
        # Look for sentence endings in reverse order
        for delimiter in ['. ', '! ', '? ']:
            last_sentence = truncated.rfind(delimiter)
            if last_sentence > max_chars * 0.5:  # Keep at least 50% of content
                return truncated[:last_sentence + 1].strip()
        
        # Fallback: find last period even without space (end of text)
        last_period = truncated.rfind('.')
        if last_period > max_chars * 0.5:
            return truncated[:last_period + 1].strip()
        
        # Last resort: return full text if we can't find good boundary
        return text
    
    async def scrape_url(self, url: str) -> Optional[List[Dict]]:
        """
        Complete scraping pipeline for one URL.
        
        Steps:
        1. Check cache
        2. Fetch HTML
        3. Extract content with trafilatura
        4. Try JSON-LD extraction
        5. Generate training data
        6. Cache results
        """
        print(f"\n📍 {urlparse(url).path}")
        
        # Check cache
        cached = self._load_cache(url)
        if cached:
            print(f"  ✓ Using cached data")
            return cached.get('training_data', [])
        
        # Fetch
        html = await self.fetch_content(url)
        if not html:
            return None
        
        # Extract with trafilatura (does all the heavy lifting)
        content = self.extract_main_content(html, url)
        if not content or not content.get('text'):
            print(f"  ✗ No content extracted")
            return None
        
        print(f"  ✓ Extracted {len(content['text'])} chars")
        
        # Try JSON-LD
        json_ld = self.extract_json_ld(html)
        if json_ld:
            print(f"  ✓ Found {len(json_ld)} JSON-LD blocks")
        
        # Detect type
        content_type = self.detect_content_type(
            content.get('title', ''),
            url,
            content.get('text', '')
        )
        print(f"  ✓ Type: {content_type}")
        
        # Generate training data
        training_data = self.generate_training_data(content, content_type)
        if not training_data:
            print(f"  ✗ No training data generated")
            return None
        
        print(f"  ✓ Generated {len(training_data)} Q&A pairs")
        
        # Cache
        self._save_cache(url, {'training_data': training_data})
        
        return training_data
    
    async def scrape_multiple(self, urls: List[str]) -> List[Dict]:
        """Scrape multiple URLs with rate limiting."""
        all_data = []
        
        for url in urls:
            data = await self.scrape_url(url)
            if data:
                all_data.extend(data)
            
            # Rate limiting: 2 seconds between requests
            await asyncio.sleep(2)
        
        return all_data
    
    def save_training_file(self, data: List[Dict], filename: str = "msu_training_data.json"):
        """Save training data in format ready for finetune.py"""
        output_path = Path(filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Saved {len(data)} examples to {filename}")
        print(f"\n📊 Stats:")
        print(f"   Total Q&A pairs: {len(data)}")
        
        # Count by type
        types = {}
        for item in data:
            ct = item.get('metadata', {}).get('content_type', 'unknown')
            types[ct] = types.get(ct, 0) + 1
        
        for ct, count in types.items():
            print(f"   {ct}: {count}")
        
        return filename


# ============================================================================
# INTERACTIVE MODE
# ============================================================================

async def interactive_mode():
    """User-friendly interactive scraping."""
    scraper = MSUDataScraper()
    
    print("\n" + "="*70)
    print("🐻 MSU DATA SCRAPER - Production Version")
    print("="*70)
    print("\nUsing: trafilatura (professional content extraction)")
    print("Output: Ready-to-train JSON format")
    print("="*70)
    
    urls = []
    
    print("\n📝 Enter URLs to scrape (one per line, empty line to finish):")
    print("Example: https://www.missouristate.edu/admissions")
    print()
    
    while True:
        url = input("URL: ").strip()
        if not url:
            break
        
        if not url.startswith('http'):
            url = f"https://www.missouristate.edu{url if url.startswith('/') else '/' + url}"
        
        urls.append(url)
        print(f"  ✓ Added ({len(urls)} total)")
    
    if not urls:
        print("\n❌ No URLs provided")
        return
    
    print(f"\n🚀 Scraping {len(urls)} URL(s)...")
    print("="*70)
    
    # Scrape
    training_data = await scraper.scrape_multiple(urls)
    
    if not training_data:
        print("\n❌ No data collected")
        return
    
    # Save
    filename = f"msu_training_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    scraper.save_training_file(training_data, filename)
    
    print(f"\n📦 Next steps:")
    print(f"   1. Review: cat {filename} | head -100")
    print(f"   2. Update finetune.py:")
    print(f'      data = load_dataset("json", data_files="{filename}", split="train")')
    print(f"   3. Train: python finetune.py")
    print()


# ============================================================================
# BATCH MODE (for power users)
# ============================================================================

async def batch_mode():
    """Batch scraping from config file."""
    scraper = MSUDataScraper()
    
    # Example configuration
    urls_config = [
        "https://www.missouristate.edu/admissions",
        "https://www.missouristate.edu/financialaid",
        "https://www.missouristate.edu/academics",
    ]
    
    print(f"\n🚀 Batch mode: {len(urls_config)} URLs")
    training_data = await scraper.scrape_multiple(urls_config)
    
    if training_data:
        scraper.save_training_file(training_data)


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point."""
    print("\n🔍 Checking dependencies...")
    
    # Check basic dependencies
    try:
        import httpx
        import trafilatura
        print("✓ httpx and trafilatura installed")
    except ImportError as e:
        print(f"\n❌ Missing basic dependencies: {e}")
        print("\nInstall with:")
        print("  pip install trafilatura httpx")
        return
    
    # Check Playwright (recommended for modern sites)
    if not PLAYWRIGHT_AVAILABLE:
        print("⚠️  Playwright not installed (recommended for JavaScript sites like MSU)")
        print("\nFor best results, install:")
        print("  pip install playwright")
        print("  playwright install chromium")
        print("\nContinuing with basic HTTP (may produce incomplete data)...")
        input("\nPress Enter to continue anyway, or Ctrl+C to cancel...")
    else:
        print("✓ Playwright available (will handle JavaScript sites)")
    
    print()
    
    try:
        asyncio.run(interactive_mode())
    except KeyboardInterrupt:
        print("\n\n👋 Cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
