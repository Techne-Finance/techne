"""Test Unified Analyzer"""
import os
import asyncio

# Load API keys from .env (not hardcoded for security)
from dotenv import load_dotenv
load_dotenv("../.env")

from services.unified_analyzer import UnifiedPoolAnalyzer

async def test():
    print("=" * 60)
    print("UNIFIED POOL ANALYZER TEST - AERODROME")
    print("=" * 60)
    
    analyzer = UnifiedPoolAnalyzer()
    
    # Test Aerodrome USDC/WETH pool (should have real swap data)
    aerodrome_usdc_weth = "0x6cDcb1C4A4D1C3C6d054b27AC5B77e89eAFb971d"
    
    print(f"\nAnalyzing Aerodrome USDC/WETH: {aerodrome_usdc_weth[:16]}...")
    
    result = await analyzer.analyze(
        aerodrome_usdc_weth, 
        protocol='aerodrome', 
        position_size_usd=5000
    )
    
    print(f"\n{'='*40}")
    print(f"RESULT:")
    print(f"{'='*40}")
    print(f"  Safe to Invest: {result['safe_to_invest']}")
    print(f"  Overall Risk:   {result['overall_risk_score']}/100")
    print(f"  Recommendation: {result['recommendation']}")
    print(f"  Analysis Time:  {result['analysis_time_ms']}ms")
    
    if result['blocking_issues']:
        print(f"\n  🚫 BLOCKING ISSUES:")
        for issue in result['blocking_issues']:
            print(f"    - {issue}")
    else:
        print(f"\n  ✅ No blocking issues")
    
    # Show tier results
    print(f"\n  Tier 1 (Scam): score={result['scam_analysis'].get('risk_score', 'N/A')}")
    wash = result['wash_analysis']
    print(f"  Tier 2 (Wash): validity={wash.get('apy_validity', 'N/A')}, traders={wash.get('unique_traders', 0)}")
    if wash.get('red_flags'):
        print(f"    🚩 Red flags: {wash['red_flags']}")
    print(f"  Tier 3 (AI):   provider={result.get('ai_analysis', {}).get('provider', 'skipped')}")
    
    await analyzer.close()

if __name__ == "__main__":
    asyncio.run(test())
