# Techne Protocol

**No-Code Builder for DeFi Trading Agents on Base**

Build, deploy, and monitor AI-powered yield farming agents without writing code.

## 🚀 Features

### 🔍 **Explore**
- Browse 100+ verified yield pools from Aerodrome, Beefy, Moonwell, Aave, Morpho
- Real-time APY from on-chain gauge data
- TVL, volume, and risk analysis
- Filter by chain, protocol, asset type

### ✅ **Verify Any Pool**
- Paste any pool URL (Aerodrome, Uniswap, Curve, SushiSwap, Beefy, Moonwell, Morpho)
- Get instant risk analysis & APY verification
- On-chain verified APY using gauge contracts
- GoPlus security screening for rug risks

### 🤖 **Build (Agent Builder)**
- No-code trading agent configuration
- Strategy presets: Stable Farmer, Balanced Growth, Yield Maximizer, Airdrop Hunter
- Protocol selection: Aerodrome, Beefy, Moonwell, Aave, Morpho, Compound
- Risk controls: Max drawdown, APY range, slippage limits
- Pro mode: Leverage, stop loss, volatility guard

### 📊 **Portfolio**
- Track all DeFi positions across protocols
- Real-time P&L monitoring
- Epoch rewards countdown

## Supported Protocols

| Protocol | Chain | APY Source |
|----------|-------|------------|
| Aerodrome | Base | ✅ On-chain gauge |
| Beefy | Multi | ✅ API |
| Moonwell | Base | ✅ API |
| Aave | Base | ✅ API |
| Morpho | Base | ✅ API |
| Curve | Multi | ✅ API |
| Uniswap V3 | Base | ✅ API |
| SushiSwap | Base | ✅ API |

## Quick Start

```bash
# Backend
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# Open http://localhost:8000
```

## Environment

```env
ALCHEMY_RPC_URL=https://base-mainnet.g.alchemy.com/v2/YOUR_KEY
```

## Tech Stack

- **Backend**: Python, FastAPI, Web3.py
- **Frontend**: Vanilla JS, HTML, CSS
- **Data**: GeckoTerminal, DefiLlama, On-chain gauges
- **RPC**: Alchemy (Base)

## License

MIT
