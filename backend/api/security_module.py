"""
Security Module - RugCheck, Data Hygiene, and Advanced Risk Scoring
Provides honeypot detection, symbol cleaning, and stablecoin peg checks.
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from web3 import Web3
import httpx

logger = logging.getLogger("SecurityModule")

# =============================================================================
# CONSTANTS
# =============================================================================

# GoPlus API for security checks
GOPLUS_BASE_URL = "https://api.gopluslabs.io/api/v1/token_security"
CHAIN_IDS = {
    "base": "8453",
    "ethereum": "1",
    "arbitrum": "42161",
    "optimism": "10",
    "polygon": "137",
}

# Known stablecoins
STABLECOINS = {
    "base": {
        "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913": "USDC",
        "0xd9aaec86b65d86f6a7b5b1b0c42ffa531710b6ca": "USDbC",
        "0x50c5725949a6f0c72e6c4a641f24049a917db0cb": "DAI",
    },
    "ethereum": {
        "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48": "USDC",
        "0xdac17f958d2ee523a2206206994597c13d831ec7": "USDT",
        "0x6b175474e89094c44da98b954eedeac495271d0f": "DAI",
    }
}

# ERC20 ABI for symbol fetching
ERC20_SYMBOL_ABI = [
    {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"type": "string"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "name", "outputs": [{"type": "string"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"type": "uint8"}], "type": "function"},
]

# RPC endpoints
RPC_ENDPOINTS = {
    "base": "https://mainnet.base.org",
    "ethereum": "https://eth.llamarpc.com",
}


class SecurityChecker:
    """
    Security module for pool verification.
    Provides RugCheck, symbol cleaning, and risk scoring.
    """
    
    def __init__(self):
        self._web3_cache: Dict[str, Web3] = {}
        logger.info("🛡️ Security Checker initialized")
    
    def _get_web3(self, chain: str) -> Optional[Web3]:
        """Get cached Web3 instance"""
        chain = chain.lower()
        if chain in self._web3_cache:
            return self._web3_cache[chain]
        
        rpc = RPC_ENDPOINTS.get(chain)
        if not rpc:
            return None
        
        try:
            w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={'timeout': 10}))
            if w3.is_connected():
                self._web3_cache[chain] = w3
                return w3
        except Exception:
            pass
        return None
    
    # =========================================================================
    # PHASE 1: GOPLUS RUGCHECK (EVM) + RUGCHECK.XYZ (SOLANA)
    # =========================================================================
    
    async def check_security(
        self, 
        token_addresses: List[str], 
        chain: str = "base"
    ) -> Dict[str, Any]:
        """
        Check token security using GoPlus API (EVM) or RugCheck.xyz (Solana).
        Returns security analysis for each token.
        """
        chain = chain.lower()
        
        # SOLANA: Use RugCheck.xyz API
        if chain == "solana":
            return await self._check_security_solana(token_addresses)
        
        # EVM: Use GoPlus API
        chain_id = CHAIN_IDS.get(chain, "8453")
        
        # Filter out invalid EVM addresses
        valid_addresses = [
            addr.lower() for addr in token_addresses 
            if addr and addr.startswith("0x") and len(addr) == 42
        ]
        
        if not valid_addresses:
            return {"status": "no_tokens", "tokens": {}}
        
        try:
            addresses_param = ",".join(valid_addresses)
            url = f"{GOPLUS_BASE_URL}/{chain_id}?contract_addresses={addresses_param}"
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url)
                
                if response.status_code != 200:
                    logger.warning(f"GoPlus API returned {response.status_code}")
                    return {"status": "api_error", "tokens": {}}
                
                data = response.json()
                result = data.get("result", {})
                
                # Process each token
                tokens_analysis = {}
                for addr, info in result.items():
                    tokens_analysis[addr.lower()] = self._analyze_token_security(info)
                
                return {
                    "status": "success",
                    "source": "goplus",
                    "tokens": tokens_analysis,
                    "summary": self._summarize_security(tokens_analysis)
                }
                
        except Exception as e:
            logger.error(f"GoPlus API failed: {e}")
            return {"status": "unknown", "error": str(e), "tokens": {}}
    
    async def _check_security_solana(self, token_addresses: List[str]) -> Dict[str, Any]:
        """
        Check Solana token security using RugCheck.xyz API.
        """
        try:
            from data_sources.rugcheck import rugcheck_client
            
            # Filter valid Solana addresses (base58, 32-44 chars)
            valid_addresses = [
                addr for addr in token_addresses 
                if addr and len(addr) >= 32 and len(addr) <= 44 and not addr.startswith("0x")
            ]
            
            if not valid_addresses:
                return {"status": "no_tokens", "source": "rugcheck", "tokens": {}}
            
            tokens_analysis = {}
            has_critical = False
            total_penalty = 0
            all_risks = []
            
            for mint in valid_addresses:
                result = await rugcheck_client.check_token(mint)
                if result:
                    tokens_analysis[mint] = {
                        "is_honeypot": result.get("is_critical", False),
                        "is_verified": True,  # Solana programs are on-chain
                        "is_mutable": result.get("is_mutable", False),
                        "has_freeze_authority": result.get("has_freeze_authority", False),
                        "risks": result.get("risks", []),
                        "score_penalty": result.get("score_penalty", 0),
                        "is_critical": result.get("is_critical", False),
                        "rugcheck_score": result.get("score", 0)
                    }
                    
                    if result.get("is_critical"):
                        has_critical = True
                    total_penalty += result.get("score_penalty", 0)
                    all_risks.extend(result.get("risks", []))
            
            return {
                "status": "success",
                "source": "rugcheck",
                "tokens": tokens_analysis,
                "summary": {
                    "total_penalty": min(total_penalty, 100),
                    "has_critical": has_critical,
                    "risk_count": len(all_risks),
                    "all_risks": all_risks[:5]  # Top 5 risks
                }
            }
            
        except Exception as e:
            logger.error(f"RugCheck API failed: {e}")
            return {"status": "error", "source": "rugcheck", "error": str(e), "tokens": {}}
    
    def _analyze_token_security(self, info: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze security info for a single token"""
        risks = []
        score_penalty = 0
        
        # Critical: Honeypot
        if info.get("is_honeypot") == "1":
            risks.append({"type": "CRITICAL", "reason": "🍯 HONEYPOT DETECTED - Cannot sell"})
            return {"is_honeypot": True, "risks": risks, "score_penalty": 100, "is_critical": True}
        
        # High: Sell tax
        try:
            sell_tax = float(info.get("sell_tax", 0)) * 100
            if sell_tax > 10:
                risks.append({"type": "HIGH", "reason": f"High sell tax: {sell_tax:.1f}%"})
                score_penalty += 30
        except (ValueError, TypeError):
            pass
        
        # High: Buy tax
        try:
            buy_tax = float(info.get("buy_tax", 0)) * 100
            if buy_tax > 10:
                risks.append({"type": "HIGH", "reason": f"High buy tax: {buy_tax:.1f}%"})
                score_penalty += 30
        except (ValueError, TypeError):
            pass
        
        # Medium: Not open source
        if info.get("is_open_source") == "0":
            risks.append({"type": "MEDIUM", "reason": "Contract not verified on explorer"})
            score_penalty += 15
        
        # High: Owner can change balance
        if info.get("owner_change_balance") == "1":
            risks.append({"type": "HIGH", "reason": "Owner can modify balances"})
            score_penalty += 25
        
        # High: Hidden owner
        if info.get("hidden_owner") == "1":
            risks.append({"type": "HIGH", "reason": "Hidden owner detected"})
            score_penalty += 20
        
        # Medium: Can take back ownership
        if info.get("can_take_back_ownership") == "1":
            risks.append({"type": "MEDIUM", "reason": "Ownership can be reclaimed"})
            score_penalty += 10
        
        return {
            "is_honeypot": False,
            "is_verified": info.get("is_open_source") == "1",
            "sell_tax": info.get("sell_tax"),
            "buy_tax": info.get("buy_tax"),
            "risks": risks,
            "score_penalty": min(score_penalty, 80),  # Cap at 80
            "is_critical": False
        }
    
    def _summarize_security(self, tokens_analysis: Dict[str, Dict]) -> Dict[str, Any]:
        """Summarize security across all tokens"""
        total_penalty = 0
        all_risks = []
        has_critical = False
        
        for addr, analysis in tokens_analysis.items():
            if analysis.get("is_critical"):
                has_critical = True
                total_penalty = 100
            else:
                total_penalty += analysis.get("score_penalty", 0)
            all_risks.extend(analysis.get("risks", []))
        
        return {
            "total_penalty": min(total_penalty, 100),
            "has_critical": has_critical,
            "risk_count": len(all_risks),
            "all_risks": all_risks
        }
    
    # =========================================================================
    # PHASE 2: SYMBOL CLEANING (Data Hygiene)
    # =========================================================================
    
    async def clean_symbol(
        self, 
        token_address: str, 
        raw_symbol: str,
        chain: str = "base"
    ) -> Tuple[str, bool]:
        """
        Clean symbol - if it's a 0x address, fetch real symbol from chain.
        Returns (cleaned_symbol, was_fixed)
        """
        if not raw_symbol:
            return await self._fetch_symbol_onchain(token_address, chain), True
        
        # Check if symbol looks like an address
        if raw_symbol.startswith("0x") and len(raw_symbol) > 10:
            clean = await self._fetch_symbol_onchain(token_address, chain)
            return (clean, True) if clean != raw_symbol else (raw_symbol, False)
        
        # Check for other garbage symbols
        if raw_symbol in ["???", "UNKNOWN", ""] or len(raw_symbol) > 20:
            clean = await self._fetch_symbol_onchain(token_address, chain)
            return (clean, True) if clean else (raw_symbol, False)
        
        return raw_symbol, False
    
    async def _fetch_symbol_onchain(self, token_address: str, chain: str) -> str:
        """Fetch token symbol directly from blockchain"""
        w3 = self._get_web3(chain)
        if not w3:
            return "???"
        
        try:
            address = Web3.to_checksum_address(token_address)
            contract = w3.eth.contract(address=address, abi=ERC20_SYMBOL_ABI)
            symbol = contract.functions.symbol().call()
            return symbol if symbol else "???"
        except Exception as e:
            logger.debug(f"Symbol fetch failed for {token_address[:10]}: {e}")
            return "???"
    
    async def clean_pool_symbols(
        self, 
        pool_data: Dict[str, Any],
        chain: str = "base"
    ) -> Dict[str, Any]:
        """
        Clean all symbols in pool data.
        Fixes symbol0, symbol1, and main symbol.
        """
        cleaned = pool_data.copy()
        warnings = []
        
        # Clean token0 symbol
        if pool_data.get("token0"):
            symbol0 = pool_data.get("symbol0", "")
            clean0, fixed0 = await self.clean_symbol(pool_data["token0"], symbol0, chain)
            cleaned["symbol0"] = clean0
            if fixed0 and clean0.startswith("0x"):
                warnings.append(f"Could not resolve symbol for token0")
        
        # Clean token1 symbol
        if pool_data.get("token1"):
            symbol1 = pool_data.get("symbol1", "")
            clean1, fixed1 = await self.clean_symbol(pool_data["token1"], symbol1, chain)
            cleaned["symbol1"] = clean1
            if fixed1 and clean1.startswith("0x"):
                warnings.append(f"Could not resolve symbol for token1")
        
        # Update main symbol
        if cleaned.get("symbol0") and cleaned.get("symbol1"):
            fee = pool_data.get("trading_fee") or pool_data.get("fee") or ""
            fee_str = f" {fee}" if fee else ""
            cleaned["symbol"] = f"{cleaned['symbol0']}/{cleaned['symbol1']}{fee_str}"
        
        if warnings:
            cleaned["symbol_warnings"] = warnings
        
        return cleaned
    
    # =========================================================================
    # PHASE 3: STABLECOIN PEG CHECK
    # =========================================================================
    
    async def check_stablecoin_peg(
        self, 
        pool_data: Dict[str, Any],
        chain: str = "base"
    ) -> Dict[str, Any]:
        """
        Check if stablecoins in pool are depegged.
        Returns peg status and warnings.
        """
        chain_stables = STABLECOINS.get(chain.lower(), {})
        token0 = pool_data.get("token0", "").lower()
        token1 = pool_data.get("token1", "").lower()
        
        # Check if this is a stablecoin pool
        is_stable_pool = pool_data.get("pool_type") == "stable"
        t0_is_stable = token0 in chain_stables
        t1_is_stable = token1 in chain_stables
        
        if not (is_stable_pool or t0_is_stable or t1_is_stable):
            return {"has_stablecoins": False, "depeg_risk": False}
        
        peg_status = {
            "has_stablecoins": True,
            "depeg_risk": False,
            "depegged_tokens": [],
            "price_warnings": []
        }
        
        # Fetch prices for stablecoins
        tokens_to_check = []
        if t0_is_stable:
            tokens_to_check.append((token0, chain_stables[token0]))
        if t1_is_stable:
            tokens_to_check.append((token1, chain_stables[token1]))
        
        for addr, name in tokens_to_check:
            price = await self._get_token_price(addr, chain)
            if price and (price < 0.98 or price > 1.02):
                peg_status["depeg_risk"] = True
                peg_status["depegged_tokens"].append({
                    "address": addr,
                    "symbol": name,
                    "price": price,
                    "deviation": abs(1 - price) * 100
                })
                peg_status["price_warnings"].append(
                    f"⚠️ {name} DEPEG: ${price:.4f} ({abs(1-price)*100:.2f}% off peg)"
                )
        
        return peg_status
    
    async def _get_token_price(self, token_address: str, chain: str) -> Optional[float]:
        """Get token price from CoinGecko"""
        try:
            chain_map = {"base": "base", "ethereum": "ethereum"}
            cg_chain = chain_map.get(chain.lower(), chain)
            
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(
                    f"https://api.coingecko.com/api/v3/simple/token_price/{cg_chain}",
                    params={"contract_addresses": token_address.lower(), "vs_currencies": "usd"}
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get(token_address.lower(), {}).get("usd")
        except Exception as e:
            logger.debug(f"Price fetch failed: {e}")
        return None
    
    # =========================================================================
    # PHASE 3B: IMPERMANENT LOSS RISK ANALYSIS
    # =========================================================================
    
    def calculate_il_risk(
        self, 
        pool_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate impermanent loss risk based on pool characteristics.
        
        IL Risk Factors:
        - Stablecoin pairs: minimal IL
        - Correlated pairs (ETH/cbETH): low IL
        - Volatile pairs (ETH/MEME): high IL
        - CL pools with narrow range: very high IL
        """
        pool_type = pool_data.get("pool_type", "volatile")
        symbol0 = (pool_data.get("symbol0", "") or "").upper()
        symbol1 = (pool_data.get("symbol1", "") or "").upper()
        is_cl = pool_data.get("is_cl") or "cl" in str(pool_type).lower()
        
        # Identify token types
        stables = {"USDC", "USDT", "DAI", "FRAX", "LUSD", "USDbC", "USDM", "BUSD"}
        eth_family = {"ETH", "WETH", "cbETH", "wstETH", "rETH", "stETH"}
        btc_family = {"BTC", "WBTC", "cbBTC", "tBTC"}
        
        t0_stable = symbol0 in stables
        t1_stable = symbol1 in stables
        t0_eth = symbol0 in eth_family
        t1_eth = symbol1 in eth_family
        t0_btc = symbol0 in btc_family
        t1_btc = symbol1 in btc_family
        
        # Determine IL risk level
        il_risk = "high"
        il_explanation = ""
        il_penalty = 15
        
        # Stable-stable: no IL
        if t0_stable and t1_stable:
            il_risk = "none"
            il_explanation = "Stablecoin pair - no impermanent loss risk"
            il_penalty = 0
        # Correlated pairs
        elif (t0_eth and t1_eth) or (t0_btc and t1_btc):
            il_risk = "low"
            il_explanation = "Correlated assets - minimal IL expected"
            il_penalty = 5
        # Stable + Blue chip
        elif (t0_stable and (t1_eth or t1_btc)) or (t1_stable and (t0_eth or t0_btc)):
            il_risk = "medium"
            il_explanation = "Stablecoin + major asset - moderate IL risk"
            il_penalty = 10
        # CL pools with narrow range
        elif is_cl:
            il_risk = "high"
            il_explanation = "Concentrated liquidity - high IL if price moves out of range"
            il_penalty = 20
        # Volatile pairs
        else:
            il_risk = "high"
            il_explanation = "Volatile pair - significant IL risk during price movements"
            il_penalty = 15
        
        return {
            "il_risk": il_risk,
            "il_explanation": il_explanation,
            "il_penalty": il_penalty,
            "is_stable_pair": t0_stable and t1_stable,
            "is_correlated": (t0_eth and t1_eth) or (t0_btc and t1_btc),
            "is_cl_pool": is_cl
        }
    
    def analyze_volatility(
        self, 
        pool_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze token volatility from available price data.
        Uses price_change_24h if available.
        """
        price_change_24h = pool_data.get("priceChange24h") or pool_data.get("price_change_24h") or 0
        
        try:
            change = abs(float(price_change_24h))
        except (ValueError, TypeError):
            change = 0
        
        # Volatility classification
        if change > 30:
            volatility = "extreme"
            vol_penalty = 25
            vol_warning = f"⚠️ EXTREME volatility: {change:.1f}% 24h price change"
        elif change > 15:
            volatility = "high"
            vol_penalty = 15
            vol_warning = f"⚠️ High volatility: {change:.1f}% 24h price change"
        elif change > 5:
            volatility = "medium"
            vol_penalty = 5
            vol_warning = None
        else:
            volatility = "low"
            vol_penalty = 0
            vol_warning = None
        
        return {
            "volatility_level": volatility,
            "price_change_24h": change,
            "volatility_penalty": vol_penalty,
            "volatility_warning": vol_warning
        }
    
    def analyze_pool_age(
        self, 
        pool_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check pool age - newer pools are riskier.
        """
        from datetime import datetime
        
        created_at = pool_data.get("pool_created_at")
        age_days = None
        age_warning = None
        age_penalty = 0
        
        if created_at:
            try:
                created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                age_days = (datetime.now(created.tzinfo) - created).days
                
                if age_days < 7:
                    age_penalty = 20
                    age_warning = f"⚠️ NEW POOL: Only {age_days} days old - higher rug risk"
                elif age_days < 30:
                    age_penalty = 10
                    age_warning = f"Pool is only {age_days} days old"
            except Exception:
                pass
        
        return {
            "pool_age_days": age_days,
            "age_penalty": age_penalty,
            "age_warning": age_warning
        }
    
    # =========================================================================
    # PHASE 4: ENHANCED RISK SCORING
    # =========================================================================
    
    def calculate_risk_score(
        self,
        pool_data: Dict[str, Any],
        security_result: Dict[str, Any],
        peg_status: Dict[str, Any],
        symbol_warnings: List[str] = None,
        # NEW: Additional risk factors
        audit_status: Dict[str, Any] = None,
        liquidity_lock: Dict[str, Any] = None,
        whale_analysis: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive risk score including IL, volatility, and pool age.
        Base score: 100, subtract penalties.
        """
        score = 100
        reasons = []
        risk_breakdown = {}
        
        # Security penalties
        security_summary = security_result.get("summary", {})
        if security_summary.get("has_critical"):
            score = 0
            reasons.append("🚨 CRITICAL: Honeypot detected - DO NOT INVEST")
            return {
                "risk_score": 0,
                "risk_level": "Critical",
                "risk_reasons": reasons,
                "is_honeypot": True,
                "risk_breakdown": {"security": "critical"}
            }
        
        security_penalty = security_summary.get("total_penalty", 0)
        if security_penalty > 0:
            score -= security_penalty
            risk_breakdown["security_penalty"] = security_penalty
            for risk in security_summary.get("all_risks", [])[:2]:  # Top 2 security risks
                reasons.append(f"🛡️ {risk['type']}: {risk['reason']}")
        
        # TVL penalties
        tvl = pool_data.get("tvl", 0) or pool_data.get("tvlUsd", 0)
        if tvl < 10000:
            score -= 20
            risk_breakdown["tvl"] = "very_low"
            reasons.append(f"💰 Very Low TVL (${tvl:,.0f}) - high slippage risk")
        elif tvl < 100000:
            score -= 10
            risk_breakdown["tvl"] = "low"
            reasons.append(f"💰 Low TVL (${tvl:,.0f}) - potential liquidity issues")
        elif tvl > 10000000:
            score += 5  # Bonus for high TVL
            risk_breakdown["tvl"] = "strong"
        
        # Depeg penalty
        if peg_status.get("depeg_risk"):
            score -= 30
            risk_breakdown["depeg"] = True
            for warning in peg_status.get("price_warnings", [])[:1]:
                reasons.append(warning)
        
        # Symbol warning penalty
        if symbol_warnings:
            score -= 10
            risk_breakdown["symbol_issues"] = True
            reasons.append("⚠️ Some token symbols could not be verified")
        
        # APY sustainability
        apy = pool_data.get("apy", 0) or 0
        if apy > 1000:
            score -= 20
            risk_breakdown["apy_sustainability"] = "extreme"
            reasons.append(f"📈 Extremely high APY ({apy:.0f}%) - likely unsustainable")
        elif apy > 500:
            score -= 10
            risk_breakdown["apy_sustainability"] = "high"
            reasons.append(f"📈 Very high APY ({apy:.0f}%) - verify sources")
        
        # === NEW: IL Risk Analysis ===
        il_analysis = self.calculate_il_risk(pool_data)
        il_penalty = il_analysis.get("il_penalty", 0)
        if il_penalty > 0:
            score -= il_penalty
            risk_breakdown["il_risk"] = il_analysis["il_risk"]
            if il_analysis["il_risk"] == "high":
                reasons.append(f"📉 {il_analysis['il_explanation']}")
        
        # === NEW: Volatility Analysis ===
        vol_analysis = self.analyze_volatility(pool_data)
        vol_penalty = vol_analysis.get("volatility_penalty", 0)
        if vol_penalty > 0:
            score -= vol_penalty
            risk_breakdown["volatility"] = vol_analysis["volatility_level"]
            if vol_analysis.get("volatility_warning"):
                reasons.append(vol_analysis["volatility_warning"])
        
        # === NEW: Pool Age Analysis ===
        age_analysis = self.analyze_pool_age(pool_data)
        age_penalty = age_analysis.get("age_penalty", 0)
        if age_penalty > 0:
            score -= age_penalty
            risk_breakdown["pool_age_days"] = age_analysis.get("pool_age_days")
            if age_analysis.get("age_warning"):
                reasons.append(age_analysis["age_warning"])
        
        # =========================================================
        # NEW: AUDIT STATUS SCORING
        # =========================================================
        if audit_status:
            is_audited = audit_status.get("audited", False)
            if is_audited:
                score += 10  # Bonus for audited protocol
                risk_breakdown["audit"] = "verified"
            else:
                score -= 5  # Penalty for unaudited
                risk_breakdown["audit"] = "unverified"
                reasons.append("📋 Protocol not verified as audited")
        
        # =========================================================
        # NEW: LIQUIDITY LOCK SCORING
        # =========================================================
        if liquidity_lock:
            has_lock = liquidity_lock.get("has_lock", False)
            if has_lock:
                score += 5  # Bonus for locked liquidity
                risk_breakdown["lock"] = "locked"
            else:
                # Only penalize for small/new pools
                if tvl < 1000000:
                    score -= 5
                    risk_breakdown["lock"] = "unlocked"
                    reasons.append("🔓 LP tokens not locked - rug risk")
        
        # =========================================================
        # NEW: WHALE CONCENTRATION SCORING
        # =========================================================
        if whale_analysis:
            lp_analysis = whale_analysis.get("lp_token") or {}
            
            # Check LP token concentration (most important)
            if lp_analysis:
                top10_pct = lp_analysis.get("top10_pct", 0) or 0
                whale_risk = lp_analysis.get("whale_risk", "unknown")
                
                if whale_risk == "high" or top10_pct > 50:
                    score -= 15
                    risk_breakdown["whale_concentration"] = "high"
                    reasons.append(f"🐳 High LP concentration: Top 10 hold {top10_pct:.0f}%")
                elif whale_risk == "medium" or top10_pct > 30:
                    score -= 5
                    risk_breakdown["whale_concentration"] = "medium"
                elif whale_risk == "low":
                    score += 3  # Small bonus for distributed
                    risk_breakdown["whale_concentration"] = "low"
        
        # =========================================================
        # NEW: REAL YIELD vs EMISSIONS SCORING
        # =========================================================
        apy_base = pool_data.get("apy_base", 0) or 0
        apy_reward = pool_data.get("apy_reward", 0) or 0
        total_apy = apy_base + apy_reward
        
        if total_apy > 0:
            real_yield_ratio = (apy_base / total_apy) * 100
            risk_breakdown["real_yield_pct"] = round(real_yield_ratio, 1)
            
            if real_yield_ratio >= 50:
                score += 5  # Bonus for sustainable yield
                risk_breakdown["yield_sustainability"] = "strong"
            elif real_yield_ratio < 10:
                score -= 5  # Penalty for emission-dependent
                risk_breakdown["yield_sustainability"] = "weak"
                if apy_reward > 50:
                    reasons.append(f"⚡ {100 - real_yield_ratio:.0f}% APY from emissions - may decrease")
        
        # Clamp score
        score = max(0, min(100, score))
        
        # Determine level
        if score >= 80:
            level = "Low"
        elif score >= 60:
            level = "Medium"
        elif score >= 30:
            level = "High"
        else:
            level = "Critical"
        
        return {
            "risk_score": score,
            "risk_level": level,
            "risk_reasons": reasons[:6],  # Top 6 reasons
            "is_honeypot": False,
            "risk_breakdown": risk_breakdown,
            # Detailed analysis
            "il_analysis": il_analysis,
            "volatility_analysis": vol_analysis,
            "pool_age_analysis": age_analysis
        }


# Singleton instance
security_checker = SecurityChecker()
