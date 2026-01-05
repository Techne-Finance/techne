---
description: Techne Finance - pełna baza wiedzy projektu
---

# Techne Finance - Knowledge Base

## 📍 Adresy & Linki
- **GitHub**: https://github.com/benjaminsmithx65-commits/techne
- **Vercel**: (ustaw po połączeniu)
- **Contract**: `0x567D1Fc55459224132aB5148c6140E8900f9a607` (Base Mainnet)
- **USDC Base**: `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`
- **Aerodrome Router**: `0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43`
- **Agent/Treasury**: `0x542c3b6cb5c93c4e4b4c20de48ee87dd79efdfec`
- **Alchemy RPC**: `https://base-mainnet.g.alchemy.com/v2/Cts9SUVykfnWx2pW5qWWS`

## 🏗️ Struktura

### Frontend (`frontend/`)
- `index.html` - Główna strona
- `app.js` - Pool explorer z filtrami
- `agent-builder-ui.js` - Konfiguracja agenta (chain/pool type selectors)
- `agent-wallet-ui.js` - NeoX-inspired deposit/withdraw UI
- `portfolio.js` - Dashboard portfolio
- `credits.js` - System kredytów (x402 USDC płatności)

### Backend (`backend/`)
- `main.py` - FastAPI endpoints
- `artisan/data_sources.py` - DefiLlama API, whitelist protokołów
- `agent_wallet.py` - Logika rebalansu agenta
- `x402/` - Płatności Meridian/x402

### Smart Contract (`contracts/`)
- `TechneAgentWallet.sol` - Vault z LP support (Aerodrome)

## ⚙️ Konfiguracja

### Base-Only Mode
- Tylko protokoły Base: Morpho, Aave, Moonwell, Compound, Aerodrome, Beefy
- default chain = "base" w API

### Pool Types
- Single-sided: lending (no IL)
- Dual-sided: LP z auto-swap przez Aerodrome

### Zmienne środowiskowe (Vercel/VPS)
```
TELEGRAM_BOT_TOKEN=xxx
AGENT_PRIVATE_KEY=xxx
WALLET_PRIVATE_KEY=xxx
```

## 🚀 Deploy Workflow
1. Push do GitHub
2. Vercel auto-deploy frontend
3. Backend: VPS lub Railway
