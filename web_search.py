"""
Web Search Module for BearChat
================================
Google Custom Search API integration with MSU-specific filtering

Features:
✓ Google Custom Search API (100 free queries/day)
✓ Strict MSU domain filtering
✓ Result validation and relevance scoring
✓ Citation formatting
✓ Caching to save API quota
✓ Fallback handling

Setup:
1. Get Google Custom Search API key: https://developers.google.com/custom-search/v1/overview
2. Create Custom Search Engine: https://programmablesearchengine.google.com/
3. Add to .env:
   GOOGLE_API_KEY=your_api_key_here
   GOOGLE_CSE_ID=your_search_engine_id_here
"""

import os
import re
import logging
import hashlib
import time
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import requests

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    print("⚠️  Google API client not installed. Run: pip install google-api-python-client")

logger = logging.getLogger(__name__)

# MSU domain whitelist - only search within these domains
MSU_DOMAINS = [
    "missouristate.edu",
    "www.missouristate.edu",
    "graduate.missouristate.edu",
    "computerscience.missouristate.edu",
    "cs.missouristate.edu",
    "biology.missouristate.edu",
    "admissions.missouristate.edu",
    "registrar.missouristate.edu",
    "library.missouristate.edu",
    "bears.missouristate.edu",
]

# MSU-specific keywords that should be in queries
MSU_KEYWORDS = [
    "missouri state",
    "msu",
    "springfield",
    "bears",
    "computer science msu",
    "cs department",
]

# Search result cache
search_cache = {}
SEARCH_CACHE_TTL = 7200  # 2 hours (conserve API quota)
SEARCH_CACHE_MAX_SIZE = 200


class WebSearchEngine:
    """Google Custom Search integration with MSU filtering"""
    
    def __init__(self, api_key: Optional[str] = None, cse_id: Optional[str] = None):
        """
        Initialize search engine
        
        Args:
            api_key: Google API key (from .env if not provided)
            cse_id: Custom Search Engine ID (from .env if not provided)
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.cse_id = cse_id or os.getenv("GOOGLE_CSE_ID")
        self.service = None
        
        if not GOOGLE_API_AVAILABLE:
            logger.warning("Google API client not available")
            return
        
        if not self.api_key or not self.cse_id:
            logger.warning("Google API credentials not configured")
            logger.info("Add GOOGLE_API_KEY and GOOGLE_CSE_ID to .env file")
            return
        
        try:
            self.service = build("customsearch", "v1", developerKey=self.api_key)
            logger.info("✓ Google Custom Search initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Google CSE: {e}")
            self.service = None
    
    def is_available(self) -> bool:
        """Check if search is available"""
        return self.service is not None
    
    def _get_cache_key(self, query: str) -> str:
        """Generate cache key for query"""
        return hashlib.md5(query.lower().strip().encode()).hexdigest()
    
    def _get_cached_results(self, cache_key: str) -> Optional[List[Dict]]:
        """Retrieve cached search results"""
        if cache_key in search_cache:
            cached_data = search_cache[cache_key]
            timestamp = cached_data.get('timestamp', 0)
            
            if time.time() - timestamp < SEARCH_CACHE_TTL:
                logger.info(f"✓ Search cache HIT: {cache_key[:8]}...")
                return cached_data['results']
            else:
                del search_cache[cache_key]
                logger.info(f"⚠ Search cache EXPIRED: {cache_key[:8]}...")
        
        return None
    
    def _cache_results(self, cache_key: str, results: List[Dict]):
        """Cache search results with LRU eviction"""
        global search_cache
        
        if len(search_cache) >= SEARCH_CACHE_MAX_SIZE:
            oldest_key = min(search_cache.keys(), 
                           key=lambda k: search_cache[k]['timestamp'])
            del search_cache[oldest_key]
        
        search_cache[cache_key] = {
            'results': results,
            'timestamp': time.time()
        }
        logger.info(f"✓ Cached search results: {cache_key[:8]}...")
    
    def _validate_msu_relevance(self, query: str) -> Tuple[bool, str]:
        """
        Validate if query is MSU-related
        
        Returns:
            (is_valid, enhanced_query)
        """
        query_lower = query.lower()
        
        # Check if query contains MSU keywords
        has_msu_keyword = any(keyword in query_lower for keyword in MSU_KEYWORDS)
        
        # If no MSU keyword, add "Missouri State University" to query
        if not has_msu_keyword:
            enhanced_query = f"Missouri State University {query}"
            logger.info(f"Enhanced query: '{query}' → '{enhanced_query}'")
            return True, enhanced_query
        
        return True, query
    
    def _filter_results_by_domain(self, results: List[Dict]) -> List[Dict]:
        """Filter results to only include MSU domains"""
        filtered = []
        
        for result in results:
            link = result.get('link', '')
            
            # Check if link is from MSU domain
            is_msu_domain = any(domain in link for domain in MSU_DOMAINS)
            
            if is_msu_domain:
                filtered.append(result)
            else:
                logger.debug(f"Filtered non-MSU domain: {link}")
        
        return filtered
    
    def _score_relevance(self, result: Dict, query: str) -> float:
        """
        Score result relevance (0.0 to 1.0)
        
        Factors:
        - MSU domain presence
        - Query keywords in title/snippet
        - URL structure
        """
        score = 0.0
        query_lower = query.lower()
        
        title = result.get('title', '').lower()
        snippet = result.get('snippet', '').lower()
        link = result.get('link', '').lower()
        
        # MSU domain bonus
        if any(domain in link for domain in MSU_DOMAINS):
            score += 0.3
        
        # Title keyword matches
        query_words = query_lower.split()
        title_matches = sum(1 for word in query_words if word in title)
        score += (title_matches / max(len(query_words), 1)) * 0.4
        
        # Snippet keyword matches
        snippet_matches = sum(1 for word in query_words if word in snippet)
        score += (snippet_matches / max(len(query_words), 1)) * 0.2
        
        # Prefer official pages
        if any(path in link for path in ['/academics/', '/programs/', '/admissions/']):
            score += 0.1
        
        return min(score, 1.0)
    
    def search(self, query: str, num_results: int = 5) -> Dict:
        """
        Perform web search with MSU filtering
        
        Args:
            query: Search query
            num_results: Number of results to return (max 10)
        
        Returns:
            {
                'success': bool,
                'results': List[Dict],
                'query_used': str,
                'total_results': int,
                'search_time': float,
                'from_cache': bool,
                'error': Optional[str]
            }
        """
        if not self.is_available():
            return {
                'success': False,
                'results': [],
                'error': 'Search service not available',
                'from_cache': False
            }
        
        start_time = time.time()
        
        # Validate and enhance query
        is_valid, enhanced_query = self._validate_msu_relevance(query)
        
        if not is_valid:
            return {
                'success': False,
                'results': [],
                'error': 'Query not relevant to Missouri State University',
                'from_cache': False
            }
        
        # Check cache
        cache_key = self._get_cache_key(enhanced_query)
        cached_results = self._get_cached_results(cache_key)
        
        if cached_results:
            return {
                'success': True,
                'results': cached_results[:num_results],
                'query_used': enhanced_query,
                'total_results': len(cached_results),
                'search_time': time.time() - start_time,
                'from_cache': True
            }
        
        try:
            # Perform Google Custom Search
            logger.info(f"Searching Google: '{enhanced_query}'")
            
            # Add site restriction to search within MSU domains
            site_restriction = " OR ".join([f"site:{domain}" for domain in MSU_DOMAINS])
            final_query = f"{enhanced_query} ({site_restriction})"
            
            result = self.service.cse().list(
                q=final_query,
                cx=self.cse_id,
                num=min(num_results, 10)  # Google CSE max is 10
            ).execute()
            
            raw_results = result.get('items', [])
            
            if not raw_results:
                logger.warning(f"No results found for: {enhanced_query}")
                return {
                    'success': True,
                    'results': [],
                    'query_used': enhanced_query,
                    'total_results': 0,
                    'search_time': time.time() - start_time,
                    'from_cache': False
                }
            
            # Filter and score results
            filtered_results = self._filter_results_by_domain(raw_results)
            
            # Add relevance scores
            for result_item in filtered_results:
                result_item['relevance_score'] = self._score_relevance(result_item, query)
            
            # Sort by relevance
            filtered_results.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            # Cache results
            self._cache_results(cache_key, filtered_results)
            
            logger.info(f"✓ Found {len(filtered_results)} MSU-relevant results")
            
            return {
                'success': True,
                'results': filtered_results[:num_results],
                'query_used': enhanced_query,
                'total_results': len(filtered_results),
                'search_time': time.time() - start_time,
                'from_cache': False
            }
            
        except HttpError as e:
            error_msg = f"Google API error: {e}"
            logger.error(error_msg)
            return {
                'success': False,
                'results': [],
                'error': error_msg,
                'from_cache': False
            }
        except Exception as e:
            error_msg = f"Search error: {e}"
            logger.error(error_msg)
            return {
                'success': False,
                'results': [],
                'error': error_msg,
                'from_cache': False
            }
    
    def format_results_for_llm(self, search_response: Dict) -> str:
        """
        Format search results as context for LLM
        
        Args:
            search_response: Response from search() method
        
        Returns:
            Formatted string for LLM prompt
        """
        if not search_response['success'] or not search_response['results']:
            return ""
        
        results = search_response['results']
        context = "### Web Search Results (Missouri State University):\n\n"
        
        for i, result in enumerate(results, 1):
            title = result.get('title', 'No title')
            snippet = result.get('snippet', 'No description')
            link = result.get('link', '')
            score = result.get('relevance_score', 0)
            
            context += f"[{i}] {title}\n"
            context += f"    {snippet}\n"
            context += f"    Source: {link}\n"
            context += f"    Relevance: {score:.2f}\n\n"
        
        return context
    
    def extract_citations(self, search_response: Dict) -> List[Dict]:
        """
        Extract citation information from search results
        
        Returns:
            List of {title, url, snippet} dicts
        """
        if not search_response['success']:
            return []
        
        citations = []
        for result in search_response['results']:
            citations.append({
                'title': result.get('title', 'Untitled'),
                'url': result.get('link', ''),
                'snippet': result.get('snippet', '')[:200]  # Truncate long snippets
            })
        
        return citations


# Singleton instance
_search_engine = None

def get_search_engine() -> WebSearchEngine:
    """Get or create search engine singleton"""
    global _search_engine
    if _search_engine is None:
        _search_engine = WebSearchEngine()
    return _search_engine


def should_use_web_search(question: str, topic: str, content_type: str) -> bool:
    """
    Determine if web search should be used for this question
    
    Criteria:
    - Not a casual conversation
    - Not a greeting
    - Topic is academic/administrative
    - Question seems to need current info
    """
    # Never search for casual/greetings
    if content_type in ["casual", "greeting"]:
        return False
    
    # Keywords that suggest current information needs
    current_info_keywords = [
        "current", "latest", "recent", "new", "updated", "2024", "2025",
        "this year", "this semester", "upcoming", "today", "now"
    ]
    
    question_lower = question.lower()
    needs_current_info = any(keyword in question_lower for keyword in current_info_keywords)
    
    # For now, enable search for all academic queries that need current info
    # You can adjust this logic based on your needs
    return needs_current_info


if __name__ == "__main__":
    # Test the search engine
    print("Testing Web Search Engine...")
    
    engine = get_search_engine()
    
    if not engine.is_available():
        print("❌ Search engine not available. Check API credentials in .env")
        exit(1)
    
    # Test queries
    test_queries = [
        "computer science master's program requirements",
        "academic calendar spring 2025",
        "CS department faculty"
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print('='*60)
        
        response = engine.search(query, num_results=3)
        
        if response['success']:
            print(f"✓ Found {response['total_results']} results")
            print(f"Search time: {response['search_time']:.2f}s")
            print(f"From cache: {response['from_cache']}")
            
            if response['results']:
                print("\nFormatted for LLM:")
                print(engine.format_results_for_llm(response))
                
                print("\nCitations:")
                citations = engine.extract_citations(response)
                for i, cite in enumerate(citations, 1):
                    print(f"{i}. {cite['title']}")
                    print(f"   {cite['url']}")
        else:
            print(f"❌ Search failed: {response.get('error')}")
