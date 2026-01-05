---
description: Techne Finance project knowledge base
---

# Techne Finance - Knowledge Base

## Project Overview
AI-powered DeFi yield optimizer on **Base chain only** (for now).

**GitHub**: https://github.com/benjaminsmithx65-commits/techne
**Description**: AI powered personal hedgefund to grow your stablecoins

## Architecture

### Frontend (`frontend/`)
- Pure HTML/JS/CSS - no framework
- Key files:
  - `app.js` - Main pool explorer logic
  - `agent-builder-ui.js` - Agent configuration
  - `agent-wallet-ui.js` - NeoX-inspired wallet UI
  - `portfolio.js` - Portfolio dashboard
  - `credits.js` - Credit system with x402 payments

### Backend (`backend/`)
- FastAPI (Python)
- Key files:
  - `main.py` - API endpoints
  - `artisan/data_sources.py` - DefiLlama, pool data
  - `agent_wallet.py` - Agent rebalancing logic

### Smart Contract (`contracts/`)
- `TechneAgentWallet.sol` - Main vault contract
- Deployed: `0x567D1Fc55459224132aB5148c6140E8900f9a607`
- Features: deposit, withdraw, LP entry via Aerodrome

## Key Decisions
1. **Base-only**: All protocols must be on Base chain
2. **Single/Dual-sided**: User can choose pool type in Build section
3. **Credits system**: 1 credit per filter use, 5 credits = 0.1 USDC
4. **NeoX-inspired**: Agent Wallet UI inspired by NeoX Agent Vaults

## Protocols Supported
- Morpho, Aave, Moonwell, Compound (lending)
- Aerodrome, Beefy (LP/vaults)

## Deployment
- **Staging**: Vercel (auto-deploy from GitHub)
- **Backend**: VPS or Railway
- **Contract**: Base Mainnet
