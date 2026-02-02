"""
Techne News Monitor - Real-time news aggregation with deduplication

Features:
- Polls multiple X/Twitter-style sources
- Deduplicates similar news (same story from multiple sources = 1 post)
- Rewrites headlines slightly to avoid exact copies
- Posts immediately to News channel when something new appears
"""

import asyncio
import logging
import re
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


@dataclass
class NewsItem:
    """Single news item."""
    title: str
    summary: str
    source: str
    category: str  # macro, security, defi, whale
    timestamp: datetime
    url: Optional[str] = None
    importance: int = 3  # 1-5
    
    @property
    def content_hash(self) -> str:
        """Hash for deduplication - based on normalized content."""
        # Normalize: lowercase, remove special chars, collapse spaces
        normalized = re.sub(r'[^\w\s]', '', self.title.lower())
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return hashlib.md5(normalized.encode()).hexdigest()[:12]


class NewsMonitor:
    """
    Real-time news monitor with deduplication.
    
    DEDUPLICATION STRATEGY:
    - Extract key terms/entities from news
    - Compare similarity with recent posts
    - If >70% similar, skip (duplicate)
    - Keep track of posted content hashes
    
    TEXT REWRITING:
    - Add emoji based on category
    - Slightly rephrase (e.g., "announces" → "revealed", "launches" → "rolls out")
    - Add our own commentary/context
    """
    
    def __init__(self):
        # Track posted items to prevent duplicates
        self._posted_hashes: Set[str] = set()
        self._recent_titles: List[str] = []  # Last 50 titles for similarity check
        self._max_recent = 50
        
        # Last fetch time per source
        self._last_fetch: Dict[str, datetime] = {}
        
        # Minimum interval between same-category posts (avoid spam)
        self._min_interval_seconds = 60
        self._last_post_time: Dict[str, datetime] = {}
        
        # IMPORTANT: Only post news that meets these criteria
        self._min_importance = 3  # Skip unimportant news (1-2)
        self._max_age_minutes = 30  # Skip old news (> 30 min old)
    
    def _is_too_old(self, item: NewsItem) -> bool:
        """Check if news is too old (only post fresh news)."""
        age = (datetime.utcnow() - item.timestamp).total_seconds() / 60
        return age > self._max_age_minutes
    
    def _is_important_enough(self, item: NewsItem) -> bool:
        """Check if news is important enough to post."""
        return item.importance >= self._min_importance
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity ratio between two texts."""
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    
    def _is_duplicate(self, item: NewsItem) -> bool:
        """
        Check if this news item is a duplicate.
        
        Uses two checks:
        1. Exact hash match (same normalized title)
        2. Similarity check with recent titles (>70% similar)
        """
        # Check 1: Exact hash
        if item.content_hash in self._posted_hashes:
            logger.debug(f"Duplicate (hash): {item.title[:50]}")
            return True
        
        # Check 2: Similarity with recent titles
        for recent in self._recent_titles:
            if self._calculate_similarity(item.title, recent) > 0.70:
                logger.debug(f"Duplicate (similarity): {item.title[:50]}")
                return True
        
        return False
    
    def _mark_as_posted(self, item: NewsItem):
        """Mark item as posted."""
        self._posted_hashes.add(item.content_hash)
        self._recent_titles.append(item.title)
        
        # Keep only recent titles
        if len(self._recent_titles) > self._max_recent:
            self._recent_titles.pop(0)
        
        self._last_post_time[item.category] = datetime.utcnow()
    
    def _can_post_category(self, category: str) -> bool:
        """Check if we can post this category (rate limiting)."""
        if category not in self._last_post_time:
            return True
        
        elapsed = (datetime.utcnow() - self._last_post_time[category]).total_seconds()
        return elapsed >= self._min_interval_seconds
    
    def _rewrite_headline(self, item: NewsItem) -> str:
        """
        Rewrite headline slightly to avoid exact copies.
        
        Transformations:
        - Add category emoji
        - Rephrase common words
        - Add context/urgency markers
        """
        title = item.title
        
        # Word replacements for variety
        replacements = [
            ("announces", "reveals"),
            ("launches", "rolls out"),
            ("partnership", "collaboration"),
            ("raises", "secures"),
            ("acquires", "takes over"),
            ("integrates", "adds support for"),
            ("reaches", "hits"),
            ("surpasses", "exceeds"),
            ("drops", "falls"),
            ("soars", "jumps"),
            ("plunges", "crashes"),
        ]
        
        # Apply one random replacement if found
        for old, new in replacements:
            if old.lower() in title.lower():
                title = re.sub(re.escape(old), new, title, flags=re.IGNORECASE, count=1)
                break
        
        # Category emoji prefix
        emoji_map = {
            "macro": "🌍",
            "security": "🚨",
            "defi": "📊",
            "whale": "🐋",
            "airdrop": "🎁",
            "breaking": "⚡",
        }
        emoji = emoji_map.get(item.category, "📰")
        
        # Importance markers
        if item.importance >= 5:
            prefix = f"{emoji} *BREAKING*"
        elif item.importance >= 4:
            prefix = f"{emoji} *ALERT*"
        else:
            prefix = f"{emoji}"
        
        return f"{prefix}\n\n*{title}*"
    
    def _format_news_post(self, item: NewsItem) -> str:
        """Format news item for Telegram post."""
        headline = self._rewrite_headline(item)
        
        # Truncate summary if too long
        summary = item.summary
        if len(summary) > 200:
            summary = summary[:197] + "..."
        
        lines = [
            headline,
            "",
            f"_{summary}_",
            "",
            f"📍 Source: {item.source}",
            f"⏰ {item.timestamp.strftime('%H:%M UTC')}",
        ]
        
        if item.url:
            lines.append(f"🔗 [Read more]({item.url})")
        
        return "\n".join(lines)
    
    async def process_news_item(self, item: NewsItem, bot, channel_id: str) -> bool:
        """
        Process a single news item.
        
        Returns True if posted, False if skipped (duplicate/rate limited/too old/unimportant).
        """
        # Check 1: Is it important enough? (skip trivial news)
        if not self._is_important_enough(item):
            logger.debug(f"Skipped (low importance {item.importance}): {item.title[:40]}")
            return False
        
        # Check 2: Is it fresh? (skip old news)
        if self._is_too_old(item):
            logger.debug(f"Skipped (too old): {item.title[:40]}")
            return False
        
        # Check 3: Is it a duplicate?
        if self._is_duplicate(item):
            return False
        
        # Check 4: Rate limiting
        if not self._can_post_category(item.category):
            logger.debug(f"Rate limited: {item.category}")
            return False
        
        # Format and post
        message = self._format_news_post(item)
        
        try:
            await bot.send_message(
                chat_id=channel_id,
                text=message,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
            
            self._mark_as_posted(item)
            logger.info(f"📰 Posted: {item.title[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to post news: {e}")
            return False
    
    async def check_and_post_news(self, news_items: List[NewsItem], bot, channel_id: str) -> int:
        """
        Process multiple news items, deduplicate and post.
        
        Returns number of items posted.
        """
        posted = 0
        
        # Sort by importance (most important first)
        sorted_items = sorted(news_items, key=lambda x: x.importance, reverse=True)
        
        for item in sorted_items:
            if await self.process_news_item(item, bot, channel_id):
                posted += 1
                # Small delay between posts
                await asyncio.sleep(2)
        
        return posted
    
    def get_stats(self) -> Dict:
        """Get monitor statistics."""
        return {
            "posted_count": len(self._posted_hashes),
            "recent_titles": len(self._recent_titles),
            "last_posts": {k: v.isoformat() for k, v in self._last_post_time.items()}
        }


# Global instance
news_monitor = NewsMonitor()


# =====================================================
# SIMULATED NEWS SOURCES (replace with real APIs)
# =====================================================

async def fetch_simulated_news() -> List[NewsItem]:
    """
    Simulate fetching news from various sources.
    In production, this would call:
    - Twitter/X API
    - News APIs
    - RSS feeds
    - On-chain event monitors
    """
    # This is placeholder - in production, fetch from real sources
    return []


async def check_for_breaking_news(bot, channel_id: str) -> int:
    """
    Main entry point for news checking.
    Called by scheduler or webhook.
    """
    try:
        news_items = await fetch_simulated_news()
        
        if not news_items:
            return 0
        
        posted = await news_monitor.check_and_post_news(news_items, bot, channel_id)
        return posted
        
    except Exception as e:
        logger.error(f"News check failed: {e}")
        return 0
