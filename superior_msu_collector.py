"""
Smart MSU Data Collector with Contextual Training Format
=========================================================
Advanced web scraper that creates high-quality, contextual training data.

Features:
- Contextual metadata (topic, source, category)
- Intelligent content cleaning (removes "Loading...", formats tables)
- Natural, varied question generation
- Multi-turn conversation format
- Better structure for model training

Usage:
    python smart_msu_collector.py
    
Date: October 2025
"""

import json
import requests
from bs4 import BeautifulSoup
import re
import time
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse
from datetime import datetime

class SmartMSUCollector:
    """Intelligent MSU content collector with contextual training data."""
    
    def __init__(self):
        self.base_url = "https://www.missouristate.edu"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        
    def clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        # Remove "Loading..." artifacts
        text = re.sub(r'\bLoading\.{3}\s*', '', text)
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove weird characters
        text = re.sub(r'[^\w\s.,;:!?()\-\'/\"&%$#@]', '', text)
        
        # Clean up spacing around punctuation
        text = re.sub(r'\s+([.,;:!?])', r'\1', text)
        
        return text.strip()
    
    def extract_structured_content(self, soup: BeautifulSoup, url: str) -> Dict:
        """Extract structured content from page with better organization."""
        
        # Get page title and main topic
        title = soup.find('h1')
        page_title = title.get_text(strip=True) if title else "MSU Information"
        
        # Remove navigation, footer, sidebar
        for element in soup.find_all(['nav', 'footer', 'aside', 'script', 'style']):
            element.decompose()
        
        content = {
            'title': self.clean_text(page_title),
            'url': url,
            'sections': [],
            'tables': [],
            'lists': [],
            'key_info': []
        }
        
        # Extract sections with headings
        for heading in soup.find_all(['h2', 'h3', 'h4']):
            section_title = self.clean_text(heading.get_text())
            if not section_title or len(section_title) < 3:
                continue
                
            # Get content after heading until next heading
            section_content = []
            for sibling in heading.find_next_siblings():
                if sibling.name in ['h2', 'h3', 'h4']:
                    break
                text = self.clean_text(sibling.get_text())
                if text and len(text) > 10:
                    section_content.append(text)
            
            if section_content:
                content['sections'].append({
                    'heading': section_title,
                    'content': ' '.join(section_content)
                })
        
        # Extract tables (like course schedules)
        for table in soup.find_all('table'):
            table_data = self.parse_table(table)
            if table_data:
                content['tables'].append(table_data)
        
        # Extract important lists
        for ul in soup.find_all(['ul', 'ol']):
            items = [self.clean_text(li.get_text()) for li in ul.find_all('li')]
            items = [item for item in items if item and len(item) > 5]
            if len(items) >= 2:
                content['lists'].append(items)
        
        # Extract key paragraphs
        for p in soup.find_all('p'):
            text = self.clean_text(p.get_text())
            if len(text) > 50:  # Meaningful paragraphs only
                content['key_info'].append(text)
        
        return content
    
    def parse_table(self, table) -> Optional[Dict]:
        """Parse HTML table into structured data."""
        headers = []
        rows = []
        
        # Get headers
        header_row = table.find('thead') or table.find('tr')
        if header_row:
            headers = [self.clean_text(th.get_text()) for th in header_row.find_all(['th', 'td'])]
            headers = [h for h in headers if h]
        
        # Get data rows
        tbody = table.find('tbody') or table
        for tr in tbody.find_all('tr'):
            cells = [self.clean_text(td.get_text()) for td in tr.find_all(['td', 'th'])]
            cells = [c for c in cells if c]
            if cells and len(cells) >= 2:
                rows.append(cells)
        
        if rows:
            return {'headers': headers, 'rows': rows}
        return None
    
    def detect_content_type(self, content: Dict) -> str:
        """Detect what type of content this is."""
        title_lower = content['title'].lower()
        url_lower = content['url'].lower()
        
        if 'degree' in title_lower or 'program' in title_lower or 'major' in title_lower:
            return 'academic_program'
        elif 'scholarship' in title_lower or 'financial aid' in title_lower:
            return 'financial_aid'
        elif 'admission' in title_lower or 'apply' in title_lower:
            return 'admissions'
        elif 'course' in title_lower and content['tables']:
            return 'course_schedule'
        elif 'housing' in title_lower or 'residence' in title_lower:
            return 'housing'
        elif 'requirement' in title_lower:
            return 'requirements'
        else:
            return 'general_info'
    
    def generate_contextual_questions(self, content: Dict, content_type: str) -> List[Dict]:
        """Generate high-quality, contextual Q&A pairs."""
        training_data = []
        topic = content['title']
        url = content['url']
        
        # Add metadata to each entry
        def create_entry(instruction: str, response: str, context_type: str = "general"):
            return {
                "instruction": instruction,
                "response": response,
                "metadata": {
                    "topic": topic,
                    "source_url": url,
                    "content_type": content_type,
                    "context_type": context_type,
                    "collected_date": datetime.now().strftime("%Y-%m-%d")
                }
            }
        
        # 1. Main overview question
        if content['key_info']:
            overview = ' '.join(content['key_info'][:3])[:500]
            training_data.append(create_entry(
                f"Tell me about {topic} at Missouri State University.",
                f"{overview}",
                "overview"
            ))
            
            training_data.append(create_entry(
                f"What is the {topic} program at MSU?",
                f"{overview}",
                "overview"
            ))
        
        # 2. Section-based questions
        for section in content['sections']:
            heading = section['heading']
            section_content = section['content'][:600]  # Limit length
            
            # Natural questions based on content type
            if content_type == 'academic_program':
                questions = [
                    f"What are the requirements for {heading} in the {topic}?",
                    f"Tell me about {heading} for {topic} students.",
                    f"Can you explain the {heading} for this program?",
                ]
            elif content_type == 'financial_aid':
                questions = [
                    f"What do I need to know about {heading}?",
                    f"How does {heading} work at MSU?",
                    f"Tell me about {heading} for students.",
                ]
            elif content_type == 'course_schedule':
                questions = [
                    f"What courses should I take in {heading}?",
                    f"Tell me about the {heading} course requirements.",
                    f"What's included in {heading}?",
                ]
            else:
                questions = [
                    f"What should I know about {heading}?",
                    f"Can you explain {heading}?",
                ]
            
            # Add 2 variations per section (not 4 identical ones!)
            for q in questions[:2]:
                training_data.append(create_entry(q, section_content, "section_detail"))
        
        # 3. Table-based questions (for degree plans, course schedules)
        for i, table in enumerate(content['tables']):
            if table['headers'] and table['rows']:
                # Format table nicely
                formatted_table = self.format_table_for_training(table)
                
                if content_type == 'course_schedule':
                    training_data.append(create_entry(
                        f"What courses are in the {topic} curriculum?",
                        formatted_table,
                        "course_list"
                    ))
                    
                    # Specific semester questions
                    if 'semester' in str(table).lower() or 'year' in str(table).lower():
                        for row in table['rows'][:4]:  # First few rows
                            if len(row) >= 2:
                                semester_name = row[0]
                                training_data.append(create_entry(
                                    f"What courses should I take in {semester_name} for {topic}?",
                                    f"In {semester_name}, you should take: {' | '.join(row[1:])}",
                                    "semester_specific"
                                ))
                else:
                    training_data.append(create_entry(
                        f"Show me the details for {topic}.",
                        formatted_table,
                        "table_data"
                    ))
        
        # 4. List-based questions
        for lst in content['lists'][:3]:  # Top 3 lists
            if len(lst) >= 2:
                list_text = '\n• ' + '\n• '.join(lst[:10])
                training_data.append(create_entry(
                    f"What are the key points about {topic}?",
                    f"Here are the important details about {topic}:{list_text}",
                    "key_points"
                ))
        
        # 5. Comparison and specific questions
        if content_type == 'academic_program':
            training_data.append(create_entry(
                f"Why should I choose the {topic}?",
                content['key_info'][0] if content['key_info'] else "This is a great program at MSU.",
                "persuasive"
            ))
            
            training_data.append(create_entry(
                f"What makes the {topic} unique at Missouri State?",
                content['key_info'][1] if len(content['key_info']) > 1 else "MSU offers excellent opportunities.",
                "unique_value"
            ))
        
        # 6. Follow-up questions
        if len(training_data) > 0:
            training_data.append(create_entry(
                f"Where can I find more information about {topic}?",
                f"You can find detailed information at {url}",
                "reference"
            ))
        
        return training_data
    
    def format_table_for_training(self, table: Dict) -> str:
        """Format table data in a readable way for training."""
        output = []
        
        if table['headers']:
            output.append(" | ".join(table['headers']))
            output.append("-" * 50)
        
        for row in table['rows'][:20]:  # Limit to 20 rows
            output.append(" | ".join(row))
        
        return '\n'.join(output)
    
    def scrape_page(self, url: str) -> Optional[Dict]:
        """Scrape and structure a single page."""
        try:
            print(f" Fetching: {url}")
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            content = self.extract_structured_content(soup, url)
            content_type = self.detect_content_type(content)
            
            print(f"Content type: {content_type}")
            print(f"Found {len(content['sections'])} sections, {len(content['tables'])} tables")
            
            return content
            
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return None
    
    def collect_and_format(self, url: str, topic_name: str) -> Optional[str]:
        """Collect data and create training file."""
        content = self.scrape_page(url)
        
        if not content:
            return None
        
        content_type = self.detect_content_type(content)
        training_data = self.generate_contextual_questions(content, content_type)
        
        if not training_data:
            print("No training data generated")
            return None
        
        # Save to file
        filename = f"smart_{topic_name}_training.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(training_data, f, indent=2, ensure_ascii=False)
        
        print(f"Created {filename} with {len(training_data)} training examples")
        
        # Show sample
        print("\n Sample training data:")
        for item in training_data[:2]:
            print(f"\n  Q: {item['instruction']}")
            print(f"  A: {item['response'][:150]}...")
            print(f"  Context: {item['metadata']['context_type']}")
        
        return filename
    
    def run_interactive(self):
        """Interactive collection mode."""
        print("\n" + "="*80)
        print("SMART MSU DATA COLLECTOR")
        print("="*80)
        print("Creates high-quality, contextual training data with metadata.")
        print("="*80)
        
        while True:
            print("\n Options:")
            print("  1. Enter MSU URL to scrape")
            print("  2. Exit")
            
            choice = input("\nChoice (1-2): ").strip()
            
            if choice == '2':
                print("\n Goodbye!")
                break
            
            if choice != '1':
                print(" Invalid choice")
                continue
            
            url = input("\n Enter MSU URL: ").strip()
            
            if not url:
                print(" No URL provided")
                continue
            
            # Ensure full URL
            if not url.startswith('http'):
                url = self.base_url + ('/' if not url.startswith('/') else '') + url

            topic = input(" Topic name (e.g., 'cs-degree-plan'): ").strip()
            if not topic:
                topic = "msu_data"
            
            # Clean topic name
            topic = re.sub(r'[^\w\-]', '_', topic.lower())

            print(f"\n Collecting data from: {url}")
            filename = self.collect_and_format(url, topic)
            
            if filename:
                print(f"\n SUCCESS! File created: {filename}")
                print("\n Next steps:")
                print(f"   1. Review: cat {filename}")
                print("   2. Update finetune.py:")
                print(f'      data = load_dataset("json", data_files="{filename}", split="train")')
                print("   3. Train: python finetune.py")
            
            again = input("\n Collect more? (y/n): ").strip().lower()
            if again != 'y':
                break
        
        print("\n Thank you for using Smart MSU Collector!")


def main():
    """Main entry point."""
    try:
        collector = SmartMSUCollector()
        collector.run_interactive()
    except KeyboardInterrupt:
        print("\n\n Interrupted by user. Exiting...")
    except Exception as e:
        print(f"\n Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
