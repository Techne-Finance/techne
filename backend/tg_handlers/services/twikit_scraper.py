"""
Techne X Scraper using Twikit library

Twikit is a Python library for Twitter API without API key.
Uses guest mode for anonymous access to fetch tweets.

Install: pip install twikit
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Try to import twikit, handle if not installed
try:
    from twikit import Client
    TWIKIT_AVAILABLE = True
except ImportError:
    TWIKIT_AVAILABLE = False
    logger.warning("Twikit not installed. Run: pip install twikit")


@dataclass
class XPost:
    """A post from X/Twitter."""
    handle: str
    content: str
    timestamp: datetime
    url: str
    category: str
    is_retweet: bool = False


class TwikitScraper:
    """
    X/Twitter scraper using Twikit library.
    
    Uses guest mode - no login required for basic scraping.
    """
    
    def __init__(self):
        self._client: Optional[Client] = None
        self._initialized = False
        
        # X accounts to track
        self._x_sources = {
            "airdrop": [
                {"handle": "defi_airdrops", "name": "DeFi Airdrops"},
                {"handle": "airdrops_one", "name": "Airdrops One"},
                {"handle": "heycape_", "name": "Cape"},
                {"handle": "DefiLlama", "name": "DefiLlama"},
                {"handle": "0xngmi", "name": "0xngmi"},
                {"handle": "definalist", "name": "DeFi Nalist"},
                {"handle": "tokenomist_ai", "name": "Tokenomist AI"},
                {"handle": "whaletrades", "name": "Whale Trades"},
                {"handle": "0xsleuth_", "name": "0xSleuth"},
                {"handle": "cryptophileee", "name": "Cryptophile"},
                {"handle": "hooeem", "name": "Hooeem"},
                {"handle": "mi_zielono", "name": "Mi Zielono"},
            ],
            "news": [
                {"handle": "solidintel_x", "name": "Solid Intel"},
                {"handle": "WalterBloomberg", "name": "Walter Bloomberg"},
                {"handle": "tree_news_feed", "name": "Tree News Feed"},
                {"handle": "LiveSquawk", "name": "LiveSquawk"},
                {"handle": "degeneratenews", "name": "Degenerate News"},
            ],
        }
        
        # Cache
        self._cache: Dict[str, List[XPost]] = {}
        self._last_fetch: Dict[str, datetime] = {}
        self._cache_ttl_seconds = 120  # 2 minutes
    
    async def _ensure_initialized(self) -> bool:
        """Initialize Twikit client."""
        if not TWIKIT_AVAILABLE:
            return False
        
        if self._initialized and self._client:
            return True
        
        try:
            self._client = Client('en-US')
            # Guest mode - no login needed
            self._initialized = True
            logger.info("Twikit client initialized in guest mode")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Twikit: {e}")
            return False
    
    async def fetch_user_tweets(self, handle: str, category: str) -> List[XPost]:
        """Fetch recent tweets from a user."""
        cache_key = f"{handle}:{category}"
        
        # Check cache
        if cache_key in self._last_fetch:
            elapsed = (datetime.utcnow() - self._last_fetch[cache_key]).total_seconds()
            if elapsed < self._cache_ttl_seconds and cache_key in self._cache:
                return self._cache[cache_key]
        
        if not await self._ensure_initialized():
            return self._cache.get(cache_key, [])
        
        posts = []
        
        try:
            # Get user
            user = await self._client.get_user_by_screen_name(handle)
            if not user:
                logger.warning(f"User not found: {handle}")
                return self._cache.get(cache_key, [])
            
            # Get user's tweets
            tweets = await self._client.get_user_tweets(user.id, 'Tweets', count=10)
            
            for tweet in tweets:
                text = tweet.text or ""
                is_retweet = text.startswith("RT @")
                
                # Parse timestamp
                try:
                    ts = datetime.strptime(tweet.created_at, "%a %b %d %H:%M:%S %z %Y")
                    ts = ts.replace(tzinfo=None)
                except:
                    ts = datetime.utcnow()
                
                posts.append(XPost(
                    handle=handle,
                    content=text[:500],
                    timestamp=ts,
                    url=f"https://x.com/{handle}/status/{tweet.id}",
                    category=category,
                    is_retweet=is_retweet
                ))
            
            # Sort and cache
            posts.sort(key=lambda x: x.timestamp, reverse=True)
            self._cache[cache_key] = posts[:10]
            self._last_fetch[cache_key] = datetime.utcnow()
            
            logger.info(f"Fetched {len(posts)} tweets from @{handle}")
            
        except Exception as e:
            logger.error(f"Error fetching @{handle}: {e}")
            return self._cache.get(cache_key, [])
        
        return posts[:10]
    
    async def fetch_category(self, category: str) -> List[XPost]:
        """Fetch all posts from accounts in a category."""
        if category not in self._x_sources:
            return []
        
        accounts = self._x_sources[category]
        all_posts = []
        
        # Fetch sequentially with delay to avoid rate limits
        for acc in accounts[:5]:  # Limit to 5 accounts per check
            try:
                posts = await self.fetch_user_tweets(acc["handle"], category)
                all_posts.extend(posts)
                await asyncio.sleep(2)  # Rate limit delay
            except Exception as e:
                logger.warning(f"Failed to fetch {acc['handle']}: {e}")
                continue
        
        all_posts.sort(key=lambda x: x.timestamp, reverse=True)
        return all_posts
    
    async def fetch_all_news_posts(self) -> List[XPost]:
        """Fetch all posts from news accounts."""
        return await self.fetch_category("news")
    
    async def fetch_all_airdrop_posts(self) -> List[XPost]:
        """Fetch all posts from airdrop accounts."""  
        return await self.fetch_category("airdrop")


# Global instance
twikit_scraper = TwikitScraper()
