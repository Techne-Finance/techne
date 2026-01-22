"""
KLUCZOWE ODKRYCIE:

Problem: Dla CL pools, stakedLiquidity/liquidity = ~99% ale to jest:
- stakedLiquidity = płynność w aktywnym tick która jest staked
- liquidity = płynność w aktywnym tick

To NIE reprezentuje rzeczywistej staked TVL!

Aerodrome pokazuje 880% APR dla $567k yearly rewards.
Wymagana staked TVL = $567k / 8.8 = $64k

Nasza kalkulacja:
- TVL: $9.74M
- Staked Ratio (z stakedLiquidity/liquidity): 99.99%  
- Staked TVL: $9.74M * 99.99% = $9.74M
- APY: $567k / $9.74M = 5.8%

Aerodrome kalkulacja:
- Używa rzeczywistej staked TVL z gauge (~$64k)
- APY: $567k / $64k = 880%

ROZWIĄZANIE: Dla CL pools NIE MOŻEMY użyć stakedLiquidity/liquidity!
Musimy albo:
1. Pobierać staked TVL z API (ale API nie działa)
2. NIE stosować staked_ratio i pokazywać "pool APR" zamiast "staker APR"
3. Oznaczać że APY jest nieznane dla CL

Najlepsze rozwiązanie: Nie stosować staked_ratio dla CL pools i pokazać
że APY może się różnić w zależności od pozycji.
"""
print("See analysis above")
