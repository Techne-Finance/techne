# Techne.finance

**AI-Powered Yield Optimizer on Base**

Pay $1 USDC → Get 5 verified yield pools for 24 hours.

## Features

- **Multi-Chain Support**: Base, Ethereum, Solana, Hyperliquid
- **Data Sources**: DefiLlama + GeckoTerminal
- **Risk Analysis**: Tooltips explaining why pools are Low/Medium/High risk
- **x402 Payments**: Pay with USDC on Base via Meridian
- **Direct Pool Links**: Jump straight to the pool on the DEX

## Quick Start (Local)

```bash
# Backend
cd backend
python -m venv venv
.\venv\Scripts\activate  # Windows
pip install -r requirements.txt
python main.py

# Open http://localhost:8000/app
```

## Environment Variables

```env
ALCHEMY_RPC_URL=https://base-mainnet.g.alchemy.com/v2/YOUR_KEY
MERIDIAN_WALLET=0xYourWalletAddress
PORT=8000
```

## Deploy to Railway

1. Push to GitHub
2. Connect Railway to repo
3. Set environment variables
4. Deploy

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/yields` | GET | Get aggregated yields |
| `/api/pro-pack/create` | POST | Create $1/5 pools session |
| `/api/pro-pack/status/{id}` | GET | Check session status |
| `/api/pro-pack/dismiss` | POST | Dismiss a pool |
| `/api/chains` | GET | List supported chains |
| `/health` | GET | Health check |

## Tech Stack

- **Backend**: Python, FastAPI, httpx
- **Frontend**: Vanilla JS, HTML, CSS
- **Blockchain**: ethers.js, web3.py
- **Data**: DefiLlama API, GeckoTerminal API

## License

MIT
