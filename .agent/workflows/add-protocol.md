---
description: Dodaj nowy protokół DeFi do Techne
---

# Dodaj Nowy Protokół

## 1. Backend - whitelist
Edytuj `backend/artisan/data_sources.py`:
```python
PROJECT_WHITELIST = [
    "morpho", "aave", "moonwell", "compound", "aerodrome", "beefy",
    "nowy-protokol"  # dodaj tutaj
]
```

## 2. Frontend - ikona w Build
Edytuj `frontend/index.html` sekcja "Agent Builder" (~linia 1117):
```html
<div class="protocol-item" data-protocol="nowy-protokol">
    <span class="protocol-icon">🆕</span>
    <span>Nowy Protokół</span>
</div>
```

## 3. Agent Builder JS
Edytuj `frontend/agent-builder-ui.js` - dodaj do presetów jeśli potrzeba.

## 4. Push
```bash
& 'C:\Program Files\Git\bin\git.exe' add .
& 'C:\Program Files\Git\bin\git.exe' commit -m "feat: add [protokol] support"
& 'C:\Program Files\Git\bin\git.exe' push
```
