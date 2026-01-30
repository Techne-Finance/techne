"""
Impermanent Loss Calculator
Calculates IL risk based on historical price volatility from CoinGecko.

Formula: IL = 2 * sqrt(price_ratio) / (1 + price_ratio) - 1
"""
import asyncio
import httpx
import math
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# CoinGecko API (free tier: 30 calls/min)
COINGECKO_API = "https://api.coingecko.com/api/v3"

# Known token mappings for Base chain
TOKEN_IDS = {
    # Stablecoins
    "USDC": "usd-coin",
    "USDT": "tether",
    "DAI": "dai",
    "FRAX": "frax",
    "USDbC": "usd-coin",  # Bridged USDC
    
    # Major tokens
    "WETH": "ethereum",
    "ETH": "ethereum",
    "CBBTC": "bitcoin",     # Coinbase wrapped BTC
    "WBTC": "wrapped-bitcoin",
    "BTC": "bitcoin",
    
    # Aerodrome
    "AERO": "aerodrome-finance",
    
    # Other popular Base tokens
    "VIRTUAL": "virtual-protocol",
    "DEGEN": "degen-base",
    "BRETT": "brett",
    "TOSHI": "toshi",
}

# Stablecoins always = $1
STABLECOINS = {"USDC", "USDT", "DAI", "FRAX", "USDBC", "EURC"}


class ILCalculator:
    """
    Calculates Impermanent Loss based on historical price volatility.
    
    Uses CoinGecko for 7-day price history to estimate volatility,
    then projects IL risk based on the pair's characteristics.
    """
    
    def __init__(self):
        self.cache: Dict[str, Dict] = {}
        self.cache_ttl = 3600  # 1 hour cache for prices
        
    def parse_symbol(self, symbol: str) -> Tuple[str, str]:
        """Parse pool symbol into token0 and token1"""
        # Handle various formats: WETH-USDC, WETH/USDC, vAMM-WETH/USDC
        symbol = symbol.upper()
        
        # Remove protocol prefixes
        for prefix in ["VAMM-", "SAMM-", "CL-", "V-", "S-"]:
            if symbol.startswith(prefix):
                symbol = symbol[len(prefix):]
        
        # Split by separator
        for sep in ["-", "/", " / "]:
            if sep in symbol:
                parts = symbol.split(sep)
                if len(parts) >= 2:
                    return parts[0].strip(), parts[1].strip()
        
        return symbol, "UNKNOWN"
    
    async def get_price_history(self, token: str, days: int = 7) -> List[float]:
        """Get historical prices from CoinGecko"""
        token = token.upper()
        
        # Stablecoins are always $1
        if token in STABLECOINS:
            return [1.0] * days
        
        # Get CoinGecko ID
        gecko_id = TOKEN_IDS.get(token)
        if not gecko_id:
            print(f"[IL] Unknown token: {token}, using fallback")
            return []
        
        # Check cache
        cache_key = f"{gecko_id}_{days}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if (datetime.now().timestamp() - cached["time"]) < self.cache_ttl:
                return cached["prices"]
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{COINGECKO_API}/coins/{gecko_id}/market_chart",
                    params={"vs_currency": "usd", "days": days}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    prices = [p[1] for p in data.get("prices", [])]
                    
                    # Cache result
                    self.cache[cache_key] = {
                        "prices": prices,
                        "time": datetime.now().timestamp()
                    }
                    return prices
        except Exception as e:
            print(f"[IL] CoinGecko error for {token}: {e}")
        
        return []
    
    def calculate_volatility(self, prices: List[float]) -> float:
        """Calculate annualized volatility from price series"""
        if len(prices) < 2:
            return 0
        
        # Calculate daily returns
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                ret = (prices[i] - prices[i-1]) / prices[i-1]
                returns.append(ret)
        
        if not returns:
            return 0
        
        # Standard deviation of returns
        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / len(returns)
        daily_vol = math.sqrt(variance)
        
        # Annualize (sqrt of trading days)
        annualized = daily_vol * math.sqrt(365)
        
        return annualized * 100  # Return as percentage
    
    def calculate_il_from_ratio(self, price_ratio: float) -> float:
        """
        Calculate IL from price ratio.
        
        IL formula: 2 * sqrt(k) / (1 + k) - 1
        where k = new_price / old_price
        """
        if price_ratio <= 0:
            return 0
        
        il = 2 * math.sqrt(price_ratio) / (1 + price_ratio) - 1
        return abs(il) * 100  # Return as positive percentage
    
    async def estimate_il(self, symbol: str, days: int = 4) -> Dict:
        """
        Estimate IL risk for a pool based on historical price movement.
        
        Uses ACTUAL max/min prices from 7d history to calculate realistic IL.
        """
        token0, token1 = self.parse_symbol(symbol)
        
        # Get price histories
        prices0 = await self.get_price_history(token0)
        prices1 = await self.get_price_history(token1)
        
        # Determine pair type
        is_stable0 = token0 in STABLECOINS
        is_stable1 = token1 in STABLECOINS
        
        if is_stable0 and is_stable1:
            # Stablecoin pair - minimal IL
            pair_type = "stablecoin"
            estimated_il = 0.01 * days
            confidence = "high"
            volatility = 0.1
        elif is_stable0 or is_stable1:
            # One stable, one volatile - use volatile token's price movement
            volatile_prices = prices1 if is_stable0 else prices0
            volatility = self.calculate_volatility(volatile_prices)
            
            if volatile_prices:
                # Calculate actual price ratio from history (max/min)
                max_price = max(volatile_prices)
                min_price = min(volatile_prices)
                if min_price > 0:
                    historical_ratio = max_price / min_price
                    # Scale by period (4 days out of 7)
                    scaled_ratio = 1 + (historical_ratio - 1) * (days / 7)
                    estimated_il = self.calculate_il_from_ratio(scaled_ratio)
                else:
                    estimated_il = 5.0  # Fallback
            else:
                # No price data - use volatility-based estimate
                estimated_il = volatility * 0.5  # Rough: IL ≈ 0.5 * volatility
            
            pair_type = "volatile"
            confidence = "medium" if volatile_prices else "low"
        else:
            # Both volatile - check relative movement
            vol0 = self.calculate_volatility(prices0)
            vol1 = self.calculate_volatility(prices1)
            volatility = max(vol0, vol1)
            
            if prices0 and prices1:
                # Calculate relative price ratio
                ratio0 = max(prices0) / min(prices0) if min(prices0) > 0 else 1
                ratio1 = max(prices1) / min(prices1) if min(prices1) > 0 else 1
                
                # Correlated assets: use difference in ratios
                # If both move together, IL is lower
                relative_ratio = abs(ratio0 - ratio1) + 1
                scaled_ratio = 1 + (relative_ratio - 1) * (days / 7) * 0.5
                estimated_il = self.calculate_il_from_ratio(scaled_ratio)
            else:
                estimated_il = volatility * 0.25  # Lower for correlated
            
            pair_type = "correlated"
            confidence = "medium" if prices0 and prices1 else "low"
        
        return {
            "symbol": symbol,
            "token0": token0,
            "token1": token1,
            "volatility_7d": round(volatility, 2),
            "estimated_il": round(estimated_il, 2),
            "pair_type": pair_type,
            "confidence": confidence,
            "period_days": days
        }


# Singleton
il_calculator = ILCalculator()


async def estimate_pool_il(symbol: str, days: int = 4) -> float:
    """Quick function to get IL estimate for a pool"""
    result = await il_calculator.estimate_il(symbol, days)
    return result["estimated_il"]


# Test
if __name__ == "__main__":
    async def test():
        calc = ILCalculator()
        
        pools = [
            "WETH-USDC",
            "USDC-USDT",
            "WETH-CBBTC",
            "AERO-USDC",
            "DEGEN-WETH",
        ]
        
        print("\n" + "="*60)
        print("IL CALCULATOR TEST (CoinGecko-based)")
        print("="*60)
        
        for symbol in pools:
            result = await calc.estimate_il(symbol, days=4)
            print(f"\n{symbol}:")
            print(f"  Type: {result['pair_type']}")
            print(f"  7d Volatility: {result['volatility_7d']:.1f}%")
            print(f"  Estimated IL (4d): {result['estimated_il']:.2f}%")
            print(f"  Confidence: {result['confidence']}")
    
    asyncio.run(test())
