# WalletWatch

WalletWatch is a Python script that fetches Bitcoin wallet transaction data from the Blockchain API and displays the wallet's transaction information, including the number of transactions, total received, total sent, and current balance in BTC.

## Features

- Fetch wallet data using the Blockchain API.
- Display wallet information in a clean and simple format.
- Allows users to enter multiple wallet addresses and view transaction details for each one.
- Calculates the total received, total sent, and balance in BTC (converted from satoshis).

## Requirements

- Python 3.x
- `requests` library

## Installation

1. Download or clone the repo:

## Usage
Run the script using Python:
```bash
python walletwatch.py
```

## Example
Enter wallet address: 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa

Wallet Address: 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
Transactions: 100
Total Received: 10.00000000 BTC
Total Sent: 5.00000000 BTC
Balance: 5.00000000 BTC

Would you like to search for another wallet? (y/n): n
[+] Goodbye!

## License
This project is licensed under the MIT License - see the LICENSE file for details.
