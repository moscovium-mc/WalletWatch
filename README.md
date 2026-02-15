# WalletWatch

A Python tool for analyzing Bitcoin wallet addresses using public blockchain data.

## Features

- View wallet balance and transaction history
- Real-time BTC to USD/EUR conversion
- Display recent transactions with timestamps
- Smart caching to reduce API calls
- Automatic retry on network failures
- Rate limiting protection

## Requirements

- Python 3.7+
- `requests` library

## Installation

Install dependencies:
```bash
pip install requests
```

## Usage

Run the script:
```bash
python walletwatch.py
```

Enter a Bitcoin address when prompted and choose how many recent transactions to display (0-50).

## Example Output

```
======================================================================
₿  Bitcoin Wallet Summary
======================================================================
Address:       1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
Transactions:  2,847
----------------------------------------------------------------------
Total Received:     68.48120000 BTC
Total Sent:          0.00000000 BTC
Total Volume:       68.48120000 BTC
----------------------------------------------------------------------
Current Balance:    68.48120000 BTC
                  3,042,453.20 USD
                  2,847,891.50 EUR

Market Price: 1 BTC = $44,425.00 USD / €41,585.00 EUR
======================================================================
Recent Transactions (last 5)
----------------------------------------------------------------------
2024-01-15 14:23 | IN  |  +0.05000000 BTC | Bal:  0.05000000 BTC
2024-01-10 09:15 | IN  |  +0.10000000 BTC | Bal:  0.10000000 BTC
...
======================================================================
```

## How It Works

- Fetches wallet data from Blockchain.info API
- Gets current BTC prices from CoinGecko API
- Caches results to minimize API calls
- Automatically retries failed requests
- Respects API rate limits

## License

MIT License - see LICENSE file for details.
