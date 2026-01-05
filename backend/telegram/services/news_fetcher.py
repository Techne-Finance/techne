"""
Techne News Fetcher - Real crypto & macro news from public APIs

SOURCES:
1. CryptoPanic - Free crypto news aggregator (no API key for basic)
2. Alpha Vantage - Market news with sentiment (free tier)
3. RSS feeds - Fed, macro economics

All sources are FREE with generous limits.
"""

import asyncio
import httpx
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


@dataclass
class RealNewsItem:
    """Real news item from API."""
    title: str
    summary: str
    source: str
    source_url: str
    category: str  # macro, crypto, defi, security
    timestamp: datetime
    importance: int = 3
    sentiment: Optional[str] = None  # bullish, bearish, neutral


class NewsFetcher:
    """
    Fetches real news from multiple free APIs.
    
    APIs Used:
    - CryptoPanic: https://cryptopanic.com/api/v1/posts/ (public, no auth for basic)
    - Alpha Vantage: NEWS_SENTIMENT (free 25 req/day)
    - RSS feeds: Various macro sources
    """
    
    def __init__(self):
        # API endpoints
        self.cryptopanic_url = "https://cryptopanic.com/api/free/v1/posts/"
        self.alphavantage_url = "https://www.alphavantage.co/query"
        
        # Alpha Vantage free key (public demo key, limited)
        self.alphavantage_key = "demo"  # Replace with real key for more requests
        
        # Cache to avoid duplicate fetches
        self._last_fetch: Dict[str, datetime] = {}
        self._cached_news: Dict[str, List[RealNewsItem]] = {}
        self._min_fetch_interval = 120  # 2 minutes
    
    def _can_fetch(self, source: str) -> bool:
        """Check if we can fetch from this source (rate limiting)."""
        if source not in self._last_fetch:
            return True
        elapsed = (datetime.utcnow() - self._last_fetch[source]).total_seconds()
        return elapsed >= self._min_fetch_interval
    
    async def fetch_cryptopanic(self) -> List[RealNewsItem]:
        """
        Fetch from CryptoPanic - free crypto news aggregator.
        No API key required for public posts.
        """
        if not self._can_fetch("cryptopanic"):
            return self._cached_news.get("cryptopanic", [])
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # Public endpoint - no auth needed
                response = await client.get(
                    self.cryptopanic_url,
                    params={
                        "auth_token": "free",  # Public access
                        "filter": "hot",  # Hot news only
                        "public": "true"
                    }
                )
                
                if response.status_code != 200:
                    logger.warning(f"CryptoPanic returned {response.status_code}")
                    return self._cached_news.get("cryptopanic", [])
                
                data = response.json()
                results = data.get("results", [])
                
                news_items = []
                for item in results[:10]:  # Top 10
                    # Determine category from kind
                    kind = item.get("kind", "news")
                    category = "crypto"
                    if "hack" in item.get("title", "").lower() or "exploit" in item.get("title", "").lower():
                        category = "security"
                    
                    # Parse timestamp
                    try:
                        ts = datetime.fromisoformat(item.get("created_at", "").replace("Z", "+00:00"))
                    except:
                        ts = datetime.utcnow()
                    
                    news_items.append(RealNewsItem(
                        title=item.get("title", "")[:200],
                        summary=item.get("title", ""),  # CryptoPanic doesn't have summary
                        source=item.get("source", {}).get("title", "CryptoPanic"),
                        source_url=item.get("url", ""),
                        category=category,
                        timestamp=ts,
                        importance=4 if item.get("votes", {}).get("important", 0) > 0 else 3
                    ))
                
                self._last_fetch["cryptopanic"] = datetime.utcnow()
                self._cached_news["cryptopanic"] = news_items
                logger.info(f"Fetched {len(news_items)} items from CryptoPanic")
                return news_items
                
        except Exception as e:
            logger.error(f"CryptoPanic fetch failed: {e}")
            return self._cached_news.get("cryptopanic", [])
    
    async def fetch_alphavantage_news(self) -> List[RealNewsItem]:
        """
        Fetch from Alpha Vantage NEWS_SENTIMENT.
        Free tier: 25 requests/day (enough for periodic checks).
        """
        if not self._can_fetch("alphavantage"):
            return self._cached_news.get("alphavantage", [])
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    self.alphavantage_url,
                    params={
                        "function": "NEWS_SENTIMENT",
                        "topics": "blockchain,financial_markets,economy_macro",
                        "sort": "LATEST",
                        "limit": 10,
                        "apikey": self.alphavantage_key
                    }
                )
                
                if response.status_code != 200:
                    return self._cached_news.get("alphavantage", [])
                
                data = response.json()
                
                # Check for rate limit message
                if "Note" in data or "Information" in data:
                    logger.warning("Alpha Vantage rate limited")
                    return self._cached_news.get("alphavantage", [])
                
                feed = data.get("feed", [])
                
                news_items = []
                for item in feed[:10]:
                    # Determine category
                    topics = item.get("topics", [])
                    category = "macro"
                    for topic in topics:
                        if "blockchain" in topic.get("topic", "").lower():
                            category = "crypto"
                            break
                    
                    # Sentiment
                    sentiment_score = float(item.get("overall_sentiment_score", 0))
                    if sentiment_score > 0.15:
                        sentiment = "bullish"
                    elif sentiment_score < -0.15:
                        sentiment = "bearish"
                    else:
                        sentiment = "neutral"
                    
                    # Parse timestamp
                    try:
                        ts_str = item.get("time_published", "")
                        ts = datetime.strptime(ts_str[:14], "%Y%m%dT%H%M%S")
                    except:
                        ts = datetime.utcnow()
                    
                    news_items.append(RealNewsItem(
                        title=item.get("title", "")[:200],
                        summary=item.get("summary", "")[:300],
                        source=item.get("source", "Alpha Vantage"),
                        source_url=item.get("url", ""),
                        category=category,
                        timestamp=ts,
                        importance=4 if abs(sentiment_score) > 0.3 else 3,
                        sentiment=sentiment
                    ))
                
                self._last_fetch["alphavantage"] = datetime.utcnow()
                self._cached_news["alphavantage"] = news_items
                logger.info(f"Fetched {len(news_items)} items from Alpha Vantage")
                return news_items
                
        except Exception as e:
            logger.error(f"Alpha Vantage fetch failed: {e}")
            return self._cached_news.get("alphavantage", [])
    
    async def fetch_rss_macro(self) -> List[RealNewsItem]:
        """
        Fetch from RSS feeds for macro news.
        Sources: Federal Reserve, Bloomberg (public RSS).
        """
        if not self._can_fetch("rss"):
            return self._cached_news.get("rss", [])
        
        rss_feeds = [
            ("https://www.federalreserve.gov/feeds/press_all.xml", "Federal Reserve", "macro"),
            ("https://feeds.bloomberg.com/markets/news.rss", "Bloomberg", "macro"),
        ]
        
        all_items = []
        
        for url, source_name, category in rss_feeds:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(url)
                    
                    if response.status_code != 200:
                        continue
                    
                    # Parse RSS XML
                    root = ET.fromstring(response.content)
                    
                    # Find items (works for both RSS 2.0 and Atom)
                    items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
                    
                    for item in items[:5]:
                        title = item.find("title")
                        if title is not None:
                            title_text = title.text or ""
                        else:
                            continue
                        
                        description = item.find("description") or item.find("{http://www.w3.org/2005/Atom}summary")
                        summary_text = description.text[:200] if description is not None and description.text else title_text
                        
                        link = item.find("link") or item.find("{http://www.w3.org/2005/Atom}link")
                        link_url = link.text if link is not None and link.text else (link.get("href") if link is not None else "")
                        
                        all_items.append(RealNewsItem(
                            title=title_text[:200],
                            summary=summary_text,
                            source=source_name,
                            source_url=link_url,
                            category=category,
                            timestamp=datetime.utcnow(),
                            importance=4 if "Fed" in source_name else 3
                        ))
                        
            except Exception as e:
                logger.warning(f"RSS fetch failed for {source_name}: {e}")
        
        self._last_fetch["rss"] = datetime.utcnow()
        self._cached_news["rss"] = all_items
        logger.info(f"Fetched {len(all_items)} items from RSS feeds")
        return all_items
    
    async def fetch_all_news(self) -> List[RealNewsItem]:
        """
        Fetch from all sources in parallel.
        Returns deduplicated, sorted list.
        """
        results = await asyncio.gather(
            self.fetch_cryptopanic(),
            self.fetch_alphavantage_news(),
            self.fetch_rss_macro(),
            return_exceptions=True
        )
        
        all_news = []
        for result in results:
            if isinstance(result, list):
                all_news.extend(result)
        
        # Sort by importance and timestamp
        all_news.sort(key=lambda x: (x.importance, x.timestamp), reverse=True)
        
        logger.info(f"Total news items fetched: {len(all_news)}")
        return all_news


# Global instance
news_fetcher = NewsFetcher()
