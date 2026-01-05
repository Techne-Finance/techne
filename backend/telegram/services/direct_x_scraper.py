"""
Techne Direct X Scraper - Uses auth tokens for direct X/Twitter access

Uses your session tokens to fetch tweets directly from X API.
No Nitter needed - direct authenticated access.
"""

import asyncio
import httpx
import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class XPost:
    """A post from X/Twitter."""
    handle: str
    content: str
    timestamp: datetime
    url: str
    category: str
    is_retweet: bool = False


class DirectXScraper:
    """
    Direct X/Twitter scraper using authenticated session.
    
    Uses ct0 and auth_token cookies to access X directly.
    """
    
    def __init__(self):
        # X session tokens (from user)
        self._ct0 = "bd417e6deeb16e3c9058dacbced9e61508dd2a4d03f2c6e65b34109b0305dab1402713b93caa2c86759b90cc55edc177132c40ce32cb6dac4d26d9094302742b88ae39fe966f262f18b49f8c364e0a4e"
        self._auth_token = "3784d475bd8b58e503dee0a3da13e253f5d1f203"
        
        # X API endpoints
        self._user_by_screen_name = "https://twitter.com/i/api/graphql/G3KGOASz96M-Qu0nwmGXNg/UserByScreenName"
        self._user_tweets = "https://twitter.com/i/api/graphql/V1ze5q3ijDS1VeLwLY0m7g/UserTweets"
        
        # Bearer token (public, used by web client)
        self._bearer = "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs=1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
        
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
        self._cache_ttl_seconds = 60  # 1 minute
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for authenticated X requests."""
        return {
            "authorization": f"Bearer {self._bearer}",
            "x-csrf-token": self._ct0,
            "cookie": f"auth_token={self._auth_token}; ct0={self._ct0}",
            "x-twitter-auth-type": "OAuth2Session",
            "x-twitter-active-user": "yes",
            "content-type": "application/json",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
    
    async def fetch_user_tweets(self, handle: str, category: str) -> List[XPost]:
        """Fetch recent tweets from a user."""
        cache_key = f"{handle}:{category}"
        
        # Check cache
        if cache_key in self._last_fetch:
            elapsed = (datetime.utcnow() - self._last_fetch[cache_key]).total_seconds()
            if elapsed < self._cache_ttl_seconds and cache_key in self._cache:
                return self._cache[cache_key]
        
        posts = []
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # First get user ID
                variables = {
                    "screen_name": handle,
                    "withSafetyModeUserFields": True
                }
                features = {
                    "hidden_profile_subscriptions_enabled": True,
                    "rweb_tipjar_consumption_enabled": True,
                    "responsive_web_graphql_exclude_directive_enabled": True,
                    "verified_phone_label_enabled": False,
                    "highlights_tweets_tab_ui_enabled": True,
                    "responsive_web_twitter_article_notes_tab_enabled": True,
                    "subscriptions_feature_can_gift_premium": True,
                    "creator_subscriptions_tweet_preview_api_enabled": True,
                    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                    "responsive_web_graphql_timeline_navigation_enabled": True
                }
                
                import json
                params = {
                    "variables": json.dumps(variables),
                    "features": json.dumps(features)
                }
                
                response = await client.get(
                    self._user_by_screen_name,
                    params=params,
                    headers=self._get_headers()
                )
                
                if response.status_code != 200:
                    logger.warning(f"Failed to get user {handle}: {response.status_code}")
                    return self._cache.get(cache_key, [])
                
                data = response.json()
                user_result = data.get("data", {}).get("user", {}).get("result", {})
                user_id = user_result.get("rest_id")
                
                if not user_id:
                    logger.warning(f"No user ID for {handle}")
                    return self._cache.get(cache_key, [])
                
                # Now fetch tweets
                tweet_variables = {
                    "userId": user_id,
                    "count": 10,
                    "includePromotedContent": False,
                    "withQuickPromoteEligibilityTweetFields": False,
                    "withVoice": True,
                    "withV2Timeline": True
                }
                tweet_features = {
                    "profile_label_improvements_pcf_label_in_post_enabled": False,
                    "rweb_tipjar_consumption_enabled": True,
                    "responsive_web_graphql_exclude_directive_enabled": True,
                    "verified_phone_label_enabled": False,
                    "creator_subscriptions_tweet_preview_api_enabled": True,
                    "responsive_web_graphql_timeline_navigation_enabled": True,
                    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                    "premium_content_api_read_enabled": False,
                    "communities_web_enable_tweet_community_results_fetch": True,
                    "c9s_tweet_anatomy_moderator_badge_enabled": True,
                    "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
                    "responsive_web_grok_analyze_post_followups_enabled": True,
                    "responsive_web_jetfuel_frame": False,
                    "responsive_web_grok_share_attachment_enabled": True,
                    "articles_preview_enabled": True,
                    "responsive_web_edit_tweet_api_enabled": True,
                    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
                    "view_counts_everywhere_api_enabled": True,
                    "longform_notetweets_consumption_enabled": True,
                    "responsive_web_twitter_article_tweet_consumption_enabled": True,
                    "tweet_awards_web_tipping_enabled": False,
                    "creator_subscriptions_quote_tweet_preview_enabled": False,
                    "freedom_of_speech_not_reach_fetch_enabled": True,
                    "standardized_nudges_misinfo": True,
                    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
                    "rweb_video_timestamps_enabled": True,
                    "longform_notetweets_rich_text_read_enabled": True,
                    "longform_notetweets_inline_media_enabled": True,
                    "responsive_web_enhance_cards_enabled": False
                }
                
                tweet_params = {
                    "variables": json.dumps(tweet_variables),
                    "features": json.dumps(tweet_features)
                }
                
                tweet_response = await client.get(
                    self._user_tweets,
                    params=tweet_params,
                    headers=self._get_headers()
                )
                
                if tweet_response.status_code != 200:
                    logger.warning(f"Failed to get tweets for {handle}: {tweet_response.status_code}")
                    return self._cache.get(cache_key, [])
                
                tweet_data = tweet_response.json()
                
                # Parse tweets from response
                timeline = tweet_data.get("data", {}).get("user", {}).get("result", {}).get("timeline_v2", {}).get("timeline", {}).get("instructions", [])
                
                for instruction in timeline:
                    entries = instruction.get("entries", [])
                    for entry in entries:
                        if "tweet" in entry.get("entryId", ""):
                            tweet_result = entry.get("content", {}).get("itemContent", {}).get("tweet_results", {}).get("result", {})
                            legacy = tweet_result.get("legacy", {})
                            
                            if not legacy:
                                continue
                            
                            text = legacy.get("full_text", "")
                            is_retweet = text.startswith("RT @")
                            
                            # Parse timestamp
                            try:
                                created_at = legacy.get("created_at", "")
                                ts = datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
                                ts = ts.replace(tzinfo=None)
                            except:
                                ts = datetime.utcnow()
                            
                            tweet_id = legacy.get("id_str", "")
                            
                            posts.append(XPost(
                                handle=handle,
                                content=text[:500],
                                timestamp=ts,
                                url=f"https://x.com/{handle}/status/{tweet_id}",
                                category=category,
                                is_retweet=is_retweet
                            ))
                
                # Sort by time and cache
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
        
        # Fetch sequentially to avoid rate limits
        for acc in accounts[:5]:  # Limit to 5 accounts per check
            posts = await self.fetch_user_tweets(acc["handle"], category)
            all_posts.extend(posts)
            await asyncio.sleep(1)  # Rate limit delay
        
        all_posts.sort(key=lambda x: x.timestamp, reverse=True)
        return all_posts
    
    async def fetch_all_news_posts(self) -> List[XPost]:
        """Fetch all posts from news accounts."""
        return await self.fetch_category("news")
    
    async def fetch_all_airdrop_posts(self) -> List[XPost]:
        """Fetch all posts from airdrop accounts."""  
        return await self.fetch_category("airdrop")


# Global instance
direct_x_scraper = DirectXScraper()
