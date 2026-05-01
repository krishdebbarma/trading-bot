# Trading Bot — Binance Futures Testnet (USDT-M)

A clean, modular Python 3 CLI that places **Market** and **Limit** orders on the Binance USDT-M Futures Testnet, plus a **TWAP** (Time-Weighted Average Price) bonus order type that splits a large order into N timed Market slices. Built with direct REST + HMAC-SHA256 (no third-party SDK), with input validation, structured logging, typed error handling, and unit tests.

---

## Project Structure

trading_bot/
├── bot/
│   ├── __init__.py
│   ├── client.py          # Binance signed REST client (HMAC-SHA256)
│   ├── orders.py          # Market / Limit / TWAP placement logic
│   ├── validators.py      # Input validation
│   └── logging_config.py  # Rotating file + console logger
├── tests/
│   └── test_validators.py # Unit tests
├── logs/                  # bot.log written here on every run
├── cli.py                 # CLI entry point (argparse)
├── README.md
├── requirements.txt
├── .env.example
└── .gitignore

### Place a MARKET order

```bash
python cli.py place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
```

### Place a LIMIT order

```bash
# BUY LIMIT must be BELOW current market
python cli.py place --symbol BTCUSDT --side BUY --type LIMIT --quantity 0.01 --price 70000

# SELL LIMIT must be ABOVE current market
python cli.py place --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 80000
```

### TWAP order (bonus — 3rd order type)

Splits `--quantity` into `--slices` equal MARKET orders, spaced `--interval` seconds apart.


## Output

Each command prints two tables — the **Order Request** summary and the **Order Response** (`orderId`, `status`, `executedQty`, `avgPrice`, etc.) — followed by a clear **SUCCESS** or red **error** panel.

---

## Logging

Every API request, response, and error is appended to **`logs/bot.log`** (rotating, 1 MB × 3 files). The console shows only warnings and errors, keeping the CLI clean.

Inspect the log:

```bash
# macOS / Linux
tail -n 50 logs/bot.log

# Windows PowerShell
Get-Content logs\bot.log -Tail 50
```

The HMAC `signature` parameter is **redacted** from logs; the API key only ever lives in the request header and is never logged.

---