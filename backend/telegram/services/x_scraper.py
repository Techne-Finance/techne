"""
Techne X/Twitter Scraper - Real-time posts from tracked accounts via Nitter RSS

Uses Nitter instances (public X mirrors) to get RSS feeds without API access.
This provides real, up-to-date posts from the X accounts user provided.

Sources: @defi_airdrops, @airdrops_one, @DefiLlama, @0xngmi, @WalterBloomberg, etc.
"""

import asyncio
import httpx
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class XPost:
    """A post from X/Twitter scraped via Nitter."""
    handle: str
    content: str
    timestamp: datetime
    url: str
    category: str  # airdrop, defi, news, alpha, whale
    is_retweet: bool = False
    engagement_hint: str = ""  # likes, retweets if available


class XScraper:
    """
    Scrapes X/Twitter posts via Nitter RSS feeds.
    
    Nitter is a privacy-friendly X frontend that provides RSS feeds.
    No API key needed - just HTTP requests.
    """
    
    def __init__(self):
        # Nitter instances (try in order, some may be down)
        self._nitter_instances = [
            "https://nitter.poast.org",
            "https://nitter.privacydev.net",
            "https://nitter.cz",
            "https://nitter.net",
            "https://nitter.1d4.us",
        ]
        
        # X accounts from user (without @)
        self._x_sources = {
            "airdrop": [
                # Airdrop Intel
                {"handle": "defi_airdrops", "name": "DeFi Airdrops"},
                {"handle": "airdrops_one", "name": "Airdrops One"},
                {"handle": "heycape_", "name": "Cape"},
                # DeFi Analytics (moved here)
                {"handle": "DefiLlama", "name": "DefiLlama"},
                {"handle": "0xngmi", "name": "0xngmi"},
                {"handle": "definalist", "name": "DeFi Nalist"},
                {"handle": "tokenomist_ai", "name": "Tokenomist AI"},
                # Whale & Alpha
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
        
        # Working Nitter instance (cached)
        self._working_instance: Optional[str] = None
        
        # Alternative: use RSS2JSON or similar services
        self._rss2json_url = "https://api.rss2json.com/v1/api.json"
    
    async def _find_working_instance(self) -> Optional[str]:
        """Find a working Nitter instance or alternative."""
        if self._working_instance:
            return self._working_instance
        
        # Try Nitter instances
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            for instance in self._nitter_instances:
                try:
                    response = await client.get(
                        f"{instance}/DefiLlama/rss",
                        headers={"User-Agent": "Mozilla/5.0 (compatible; TechneBot)"}
                    )
                    if response.status_code == 200 and ("<rss" in response.text or "<feed" in response.text):
                        self._working_instance = instance
                        logger.info(f"Found working Nitter instance: {instance}")
                        return instance
                except Exception as e:
                    logger.debug(f"Nitter {instance} failed: {e}")
                    continue
        
        logger.warning("No working Nitter instance found - using simulated data")
        return None
    
    async def fetch_account_rss(self, handle: str, category: str) -> List[XPost]:
        """Fetch RSS feed for a single X account via Nitter."""
        cache_key = f"{handle}:{category}"
        
        # Check cache
        if cache_key in self._last_fetch:
            elapsed = (datetime.utcnow() - self._last_fetch[cache_key]).total_seconds()
            if elapsed < self._cache_ttl_seconds and cache_key in self._cache:
                return self._cache[cache_key]
        
        instance = await self._find_working_instance()
        if not instance:
            return self._cache.get(cache_key, [])
        
        posts = []
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                url = f"{instance}/{handle}/rss"
                response = await client.get(url)
                
                if response.status_code != 200:
                    logger.warning(f"Failed to fetch {handle}: {response.status_code}")
                    return self._cache.get(cache_key, [])
                
                # Parse RSS
                root = ET.fromstring(response.content)
                items = root.findall(".//item")
                
                for item in items[:10]:  # Last 10 posts
                    title_elem = item.find("title")
                    link_elem = item.find("link")
                    pub_date_elem = item.find("pubDate")
                    description_elem = item.find("description")
                    
                    if title_elem is None or title_elem.text is None:
                        continue
                    
                    content = title_elem.text
                    
                    # Check if retweet
                    is_retweet = content.startswith("RT @") or content.startswith("R to @")
                    
                    # Parse timestamp
                    try:
                        if pub_date_elem is not None and pub_date_elem.text:
                            # Format: "Mon, 01 Jan 2026 12:00:00 GMT"
                            ts = datetime.strptime(
                                pub_date_elem.text, 
                                "%a, %d %b %Y %H:%M:%S %Z"
                            )
                        else:
                            ts = datetime.utcnow()
                    except:
                        ts = datetime.utcnow()
                    
                    posts.append(XPost(
                        handle=handle,
                        content=content[:500],
                        timestamp=ts,
                        url=link_elem.text if link_elem is not None and link_elem.text else "",
                        category=category,
                        is_retweet=is_retweet
                    ))
                
                self._cache[cache_key] = posts
                self._last_fetch[cache_key] = datetime.utcnow()
                logger.debug(f"Fetched {len(posts)} posts from @{handle}")
                
        except Exception as e:
            logger.error(f"Error fetching @{handle}: {e}")
            return self._cache.get(cache_key, [])
        
        return posts
    
    async def fetch_category(self, category: str) -> List[XPost]:
        """Fetch all posts from accounts in a category."""
        if category not in self._x_sources:
            return []
        
        accounts = self._x_sources[category]
        all_posts = []
        
        # Fetch in parallel
        tasks = [
            self.fetch_account_rss(acc["handle"], category) 
            for acc in accounts
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                all_posts.extend(result)
        
        # Sort by timestamp (newest first)
        all_posts.sort(key=lambda x: x.timestamp, reverse=True)
        return all_posts
    
    async def fetch_all_airdrop_posts(self) -> List[XPost]:
        """Fetch all posts from airdrop-related accounts."""
        return await self.fetch_category("airdrop")
    
    async def fetch_all_news_posts(self) -> List[XPost]:
        """Fetch all posts from news accounts."""
        return await self.fetch_category("news")
    
    async def fetch_all(self) -> List[XPost]:
        """Fetch from all categories."""
        all_posts = []
        for category in self._x_sources.keys():
            posts = await self.fetch_category(category)
            all_posts.extend(posts)
        
        # Sort by timestamp and dedupe
        all_posts.sort(key=lambda x: x.timestamp, reverse=True)
        return all_posts[:50]  # Top 50 most recent
    
    def filter_airdrop_mentions(self, posts: List[XPost]) -> List[XPost]:
        """Filter posts that mention airdrops, points, or token launches."""
        keywords = [
            "airdrop", "points", "token launch", "TGE", "snapshot",
            "claim", "eligible", "distribution", "allocation",
            "farming", "testnet", "mainnet", "announcement"
        ]
        
        filtered = []
        for post in posts:
            content_lower = post.content.lower()
            if any(kw in content_lower for kw in keywords):
                filtered.append(post)
        
        return filtered
    
    def format_for_telegram(self, posts: List[XPost], limit: int = 5) -> str:
        """Format posts for Telegram message."""
        if not posts:
            return "No recent posts found."
        
        message = ""
        for post in posts[:limit]:
            # Clean content
            content = post.content[:200]
            if len(post.content) > 200:
                content += "..."
            
            # Format
            time_ago = self._time_ago(post.timestamp)
            emoji = "🔄" if post.is_retweet else "📢"
            
            message += f"""
{emoji} *@{post.handle}* ({time_ago})
_{content}_
[View]({post.url})
"""
        
        return message
    
    def _time_ago(self, dt: datetime) -> str:
        """Format timestamp as 'X ago'."""
        delta = datetime.utcnow() - dt
        if delta.days > 0:
            return f"{delta.days}d ago"
        elif delta.seconds > 3600:
            return f"{delta.seconds // 3600}h ago"
        elif delta.seconds > 60:
            return f"{delta.seconds // 60}m ago"
        else:
            return "just now"


# Global instance
x_scraper = XScraper()
