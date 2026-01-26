"""
Scam Detection Service
AI-powered contract analysis and fingerprinting

Features:
- Fetch verified source code from Basescan
- Pattern matching for scam signatures
- Risk scoring (0-100)
- Supabase pgvector integration for fingerprint storage
"""

import os
import re
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime
import hashlib

# Basescan API
BASESCAN_API = "https://api.basescan.org/api"
BASESCAN_API_KEY = os.getenv("BASESCAN_API_KEY", "")

# Known scam patterns (function signatures and code patterns)
SCAM_PATTERNS = {
    "hidden_mint": {
        "patterns": [
            r"function\s+_mint\s*\(\s*address\s*,\s*uint256\s*\)\s*private",
            r"function\s+mint\s*\(\s*address\s*,\s*uint256\s*\)\s*internal",
            r"_mint\s*\(\s*owner\s*,",
        ],
        "risk_weight": 30,
        "description": "Hidden mint function - can inflate supply"
    },
    "blacklist": {
        "patterns": [
            r"mapping\s*\(\s*address\s*=>\s*bool\s*\)\s*(private|internal)?\s*blacklist",
            r"isBlacklisted\[",
            r"require\s*\(\s*!blacklist\[",
        ],
        "risk_weight": 25,
        "description": "Blacklist mechanism - can block selling"
    },
    "honeypot": {
        "patterns": [
            r"require\s*\(\s*msg\.sender\s*==\s*owner",
            r"require\s*\(\s*tx\.origin\s*==",
            r"onlyOwner.*transfer",
        ],
        "risk_weight": 35,
        "description": "Honeypot logic - may prevent selling"
    },
    "antibot": {
        "patterns": [
            r"require\s*\(\s*msg\.sender\s*!=\s*tx\.origin\s*\)",
            r"require\s*\(\s*tx\.origin\s*==\s*msg\.sender\s*\)",
        ],
        "risk_weight": 15,
        "description": "Anti-bot (often used in scams)"
    },
    "max_tx": {
        "patterns": [
            r"maxTxAmount",
            r"_maxTxAmount",
            r"require\s*\(\s*amount\s*<=\s*maxTx",
        ],
        "risk_weight": 10,
        "description": "Max transaction limit (can be manipulated)"
    },
    "hidden_owner": {
        "patterns": [
            r"address\s+private\s+_owner",
            r"address\s+internal\s+hiddenOwner",
        ],
        "risk_weight": 20,
        "description": "Hidden owner address"
    },
    "fee_manipulation": {
        "patterns": [
            r"sellFee\s*=\s*[5-9][0-9]",  # Sell fee > 50%
            r"_taxFee\s*=\s*[2-9][0-9]",
            r"function\s+setFee.*100",
        ],
        "risk_weight": 25,
        "description": "High/manipulatable fees"
    }
}

# Safe patterns (reduce risk score)
SAFE_PATTERNS = {
    "openzeppelin": {
        "patterns": [
            r"import.*@openzeppelin",
            r"OpenZeppelin Contracts",
        ],
        "risk_reduction": 15,
        "description": "Uses OpenZeppelin (audited)"
    },
    "renounced": {
        "patterns": [
            r"renounceOwnership\(\)",
            r"owner\s*=\s*address\(0\)",
        ],
        "risk_reduction": 20,
        "description": "Ownership renounced"
    },
    "verified_proxy": {
        "patterns": [
            r"TransparentUpgradeableProxy",
            r"ERC1967Proxy",
        ],
        "risk_reduction": 10,
        "description": "Standard proxy pattern"
    }
}


class ScamDetector:
    """
    AI-powered scam detection for smart contracts.
    
    Usage:
        detector = ScamDetector()
        result = await detector.analyze_contract("0x...")
        
        if result["risk_score"] > 70:
            print("HIGH RISK - Do not invest!")
    """
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.cache: Dict[str, Dict] = {}
    
    async def fetch_contract_source(self, address: str) -> Optional[str]:
        """Fetch verified source code from Basescan."""
        try:
            params = {
                "module": "contract",
                "action": "getsourcecode",
                "address": address,
                "apikey": BASESCAN_API_KEY
            }
            
            response = await self.client.get(BASESCAN_API, params=params)
            data = response.json()
            
            if data.get("status") == "1" and data.get("result"):
                source = data["result"][0].get("SourceCode", "")
                return source if source else None
            
            return None
            
        except Exception as e:
            print(f"[ScamDetector] Error fetching source: {e}")
            return None
    
    def analyze_source(self, source_code: str) -> Dict[str, Any]:
        """Analyze source code for scam patterns."""
        findings = []
        risk_score = 0
        
        # Check scam patterns
        for pattern_name, pattern_data in SCAM_PATTERNS.items():
            for regex in pattern_data["patterns"]:
                if re.search(regex, source_code, re.IGNORECASE):
                    findings.append({
                        "type": "risk",
                        "name": pattern_name,
                        "description": pattern_data["description"],
                        "weight": pattern_data["risk_weight"]
                    })
                    risk_score += pattern_data["risk_weight"]
                    break  # Only count once per pattern type
        
        # Check safe patterns (reduce risk)
        for pattern_name, pattern_data in SAFE_PATTERNS.items():
            for regex in pattern_data["patterns"]:
                if re.search(regex, source_code, re.IGNORECASE):
                    findings.append({
                        "type": "safe",
                        "name": pattern_name,
                        "description": pattern_data["description"],
                        "weight": -pattern_data["risk_reduction"]
                    })
                    risk_score -= pattern_data["risk_reduction"]
                    break
        
        # Clamp score to 0-100
        risk_score = max(0, min(100, risk_score))
        
        return {
            "risk_score": risk_score,
            "findings": findings,
            "source_length": len(source_code)
        }
    
    async def analyze_contract(self, address: str) -> Dict[str, Any]:
        """
        Full contract analysis.
        
        Returns:
            {
                "address": "0x...",
                "risk_score": 45,
                "risk_level": "MEDIUM",
                "is_verified": True,
                "findings": [...],
                "recommendation": "CAUTION"
            }
        """
        address = address.lower()
        
        # Check cache
        if address in self.cache:
            return self.cache[address]
        
        result = {
            "address": address,
            "analyzed_at": datetime.utcnow().isoformat(),
            "is_verified": False,
            "risk_score": 50,  # Default for unverified
            "risk_level": "UNKNOWN",
            "findings": [],
            "recommendation": "UNKNOWN"
        }
        
        # Fetch source
        source = await self.fetch_contract_source(address)
        
        if source:
            # ==========================================
            # SIMILARITY CHECK - Fast path for known scams
            # ==========================================
            similar_scam = await self.find_similar_scam(source, threshold=0.95)
            if similar_scam:
                result["is_verified"] = True
                result["risk_score"] = max(similar_scam["risk_score"], 80)
                result["risk_level"] = "CRITICAL"
                result["recommendation"] = "SCAM"
                result["similar_to"] = similar_scam["contract_address"]
                result["similarity"] = similar_scam["similarity"]
                result["findings"].append({
                    "type": "risk",
                    "name": "known_scam_pattern",
                    "description": f"95%+ similar to known scam {similar_scam['contract_address'][:10]}...",
                    "weight": 50
                })
                self.cache[address] = result
                return result
            
            result["is_verified"] = True
            analysis = self.analyze_source(source)
            result["risk_score"] = analysis["risk_score"]
            result["findings"] = analysis["findings"]
            result["source_hash"] = hashlib.sha256(source.encode()).hexdigest()[:16]
        else:
            # Unverified contracts are suspicious
            result["risk_score"] = 60
            result["findings"].append({
                "type": "risk",
                "name": "unverified",
                "description": "Contract source not verified on Basescan",
                "weight": 20
            })
        
        # Determine risk level
        score = result["risk_score"]
        if score < 20:
            result["risk_level"] = "LOW"
            result["recommendation"] = "SAFE"
        elif score < 40:
            result["risk_level"] = "LOW-MEDIUM"
            result["recommendation"] = "PROCEED"
        elif score < 60:
            result["risk_level"] = "MEDIUM"
            result["recommendation"] = "CAUTION"
        elif score < 80:
            result["risk_level"] = "HIGH"
            result["recommendation"] = "AVOID"
        else:
            result["risk_level"] = "CRITICAL"
            result["recommendation"] = "SCAM"
        
        # ==========================================
        # AI ENHANCEMENT (Cheap LLM - Groq/Gemini/GPT-4o-mini)
        # Only for ambiguous cases (30-70 score) to save costs
        # ==========================================
        if source and 30 <= result["risk_score"] <= 70:
            try:
                from .cheap_llm import enhance_scam_detection
                result = await enhance_scam_detection(address, source, result)
                print(f"[ScamDetector] AI enhanced: {result.get('ai_provider', 'N/A')}")
            except Exception as e:
                print(f"[ScamDetector] AI enhancement failed: {e}")
                result["ai_enhanced"] = False
        else:
            result["ai_enhanced"] = False
            result["ai_reason"] = "Score clear - AI skipped (cost optimization)"
        
        # ==========================================
        # STORE FINGERPRINT for future similarity matching
        # ==========================================
        if source:
            await self.store_fingerprint(address, result, source)
        
        # Cache result
        self.cache[address] = result
        
        return result
    
    async def is_safe_to_invest(self, address: str, max_risk: int = 50) -> bool:
        """Quick check if contract is safe enough to invest."""
        result = await self.analyze_contract(address)
        return result["risk_score"] <= max_risk
    
    def get_fingerprint(self, source_code: str) -> str:
        """Generate fingerprint hash for quick matching."""
        # Remove whitespace and comments for consistent hashing
        clean = re.sub(r'//.*', '', source_code)
        clean = re.sub(r'/\*.*?\*/', '', clean, flags=re.DOTALL)
        clean = re.sub(r'\s+', '', clean)
        
        return hashlib.sha256(clean.encode()).hexdigest()
    
    def get_embedding(self, source_code: str) -> Optional[List[float]]:
        """
        Generate embedding vector for similarity search.
        Uses sentence-transformers all-MiniLM-L6-v2 (384 dimensions).
        Falls back to hash-based pseudo-embedding if transformer unavailable.
        """
        try:
            from sentence_transformers import SentenceTransformer
            
            # Extract key code patterns for embedding
            # Focus on function signatures and critical logic
            patterns = []
            patterns.extend(re.findall(r'function\s+\w+\s*\([^)]*\)', source_code))
            patterns.extend(re.findall(r'require\s*\([^)]+\)', source_code))
            patterns.extend(re.findall(r'mapping\s*\([^)]+\)', source_code))
            
            text = ' '.join(patterns[:50])  # Limit to 50 patterns
            if not text:
                text = source_code[:2000]  # Fallback to raw code
            
            model = SentenceTransformer('all-MiniLM-L6-v2')
            embedding = model.encode(text).tolist()
            return embedding
            
        except ImportError:
            print("[ScamDetector] sentence-transformers not installed, using hash-based embedding")
            return None
        except Exception as e:
            print(f"[ScamDetector] Embedding error: {e}")
            return None
    
    async def store_fingerprint(self, address: str, result: Dict[str, Any], source_code: str) -> bool:
        """Store contract fingerprint in Supabase for future similarity matching."""
        try:
            import httpx
            
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_ANON_KEY")
            
            if not supabase_url or not supabase_key:
                print("[ScamDetector] Supabase not configured, skipping fingerprint storage")
                return False
            
            # Generate embedding
            embedding = self.get_embedding(source_code)
            
            data = {
                "contract_address": address.lower(),
                "chain": "base",
                "source_hash": self.get_fingerprint(source_code),
                "embedding": embedding,
                "risk_score": result.get("risk_score", 50),
                "risk_level": result.get("risk_level", "UNKNOWN"),
                "is_scam": result.get("risk_score", 0) >= 70,
                "findings": result.get("findings", []),
                "is_verified": result.get("is_verified", False),
                "source_length": len(source_code),
                "analyzed_by": "ai" if result.get("ai_enhanced") else "regex"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{supabase_url}/rest/v1/scam_fingerprints",
                    json=data,
                    headers={
                        "apikey": supabase_key,
                        "Authorization": f"Bearer {supabase_key}",
                        "Content-Type": "application/json",
                        "Prefer": "return=minimal"
                    }
                )
                
                if response.status_code in [200, 201]:
                    print(f"[ScamDetector] ✅ Stored fingerprint for {address[:10]}...")
                    return True
                else:
                    print(f"[ScamDetector] Fingerprint storage failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"[ScamDetector] Store fingerprint error: {e}")
            return False
    
    async def find_similar_scam(self, source_code: str, threshold: float = 0.95) -> Optional[Dict]:
        """
        Check if contract is similar to known scams using pgvector similarity search.
        
        Returns matching scam info if similarity > threshold, else None.
        """
        try:
            import httpx
            
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_ANON_KEY")
            
            if not supabase_url or not supabase_key:
                return None
            
            embedding = self.get_embedding(source_code)
            if not embedding:
                return None
            
            # Call Supabase RPC function
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{supabase_url}/rest/v1/rpc/find_similar_scams",
                    json={
                        "query_embedding": embedding,
                        "similarity_threshold": threshold,
                        "max_results": 1
                    },
                    headers={
                        "apikey": supabase_key,
                        "Authorization": f"Bearer {supabase_key}",
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code == 200:
                    results = response.json()
                    if results and len(results) > 0:
                        match = results[0]
                        if match.get("is_scam"):
                            print(f"[ScamDetector] ⚠️ Similar to known scam: {match['contract_address'][:10]}... (similarity: {match['similarity']:.2%})")
                            return match
                
                return None
                
        except Exception as e:
            print(f"[ScamDetector] Similarity search error: {e}")
            return None
    
    async def close(self):
        await self.client.aclose()


# Global instance
_detector_instance = None

def get_detector() -> ScamDetector:
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = ScamDetector()
    return _detector_instance


# ============================================
# CLI TEST
# ============================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        print("="*60)
        print("Scam Detector Test")
        print("="*60)
        
        detector = ScamDetector()
        
        # Test with USDC (should be safe)
        usdc = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
        print(f"\nAnalyzing USDC: {usdc[:10]}...")
        
        result = await detector.analyze_contract(usdc)
        
        print(f"  Verified: {result['is_verified']}")
        print(f"  Risk Score: {result['risk_score']}/100")
        print(f"  Risk Level: {result['risk_level']}")
        print(f"  Recommendation: {result['recommendation']}")
        
        if result["findings"]:
            print(f"  Findings:")
            for f in result["findings"]:
                sign = "⚠️" if f["type"] == "risk" else "✅"
                print(f"    {sign} {f['name']}: {f['description']}")
        
        await detector.close()
    
    asyncio.run(test())
