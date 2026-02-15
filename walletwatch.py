import requests
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
import json


# ============================================================================
# RATE LIMITER
# ============================================================================

class RateLimiter:
    """Simple rate limiter to prevent API abuse"""
    
    def __init__(self, calls_per_minute: int = 10):
        self.calls_per_minute = calls_per_minute
        self.calls: List[float] = []
    
    def wait_if_needed(self) -> None:
        """Block if rate limit would be exceeded"""
        now = time.time()
        # Remove calls older than 1 minute
        self.calls = [call_time for call_time in self.calls if now - call_time < 60]
        
        if len(self.calls) >= self.calls_per_minute:
            # Calculate how long to wait
            oldest_call = self.calls[0]
            wait_time = 60 - (now - oldest_call) + 0.1  # Add small buffer
            if wait_time > 0:
                print(f"[!] Rate limit: waiting {wait_time:.1f}s...")
                time.sleep(wait_time)
                self.calls = []
        
        self.calls.append(time.time())


# ============================================================================
# CACHING DECORATOR
# ============================================================================

def timed_cache(seconds: int = 300):
    """Cache decorator with time-based expiration"""
    def decorator(func):
        cache: Dict[str, tuple[Any, float]] = {}
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from arguments
            key = str(args) + str(kwargs)
            
            if key in cache:
                result, timestamp = cache[key]
                if time.time() - timestamp < seconds:
                    print(f"[+] Using cached result (age: {int(time.time() - timestamp)}s)")
                    return result
            
            # Call function and cache result
            result = func(*args, **kwargs)
            cache[key] = (result, time.time())
            return result
        
        return wrapper
    return decorator


# ============================================================================
# RETRY DECORATOR
# ============================================================================

def retry_with_backoff(max_attempts: int = 3, base_delay: float = 1.0):
    """Retry decorator with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.RequestException as e:
                    if attempt == max_attempts - 1:
                        raise
                    
                    delay = base_delay * (2 ** attempt)
                    print(f"[!] Attempt {attempt + 1} failed: {e}")
                    print(f"[!] Retrying in {delay:.1f}s...")
                    time.sleep(delay)
            
            return None
        
        return wrapper
    return decorator


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class Transaction:
    """Individual transaction data"""
    hash: str
    time: datetime
    amount: float  # BTC (can be negative for outgoing)
    balance_after: float  # BTC
    
    def __str__(self) -> str:
        direction = "OUT" if self.amount < 0 else "IN "
        sign = "" if self.amount < 0 else "+"
        return (
            f"{self.time.strftime('%Y-%m-%d %H:%M')} | "
            f"{direction} | {sign}{self.amount:>12.8f} BTC | "
            f"Bal: {self.balance_after:>12.8f} BTC"
        )


@dataclass
class FiatPrice:
    """Current BTC prices in fiat"""
    usd: float
    eur: float
    timestamp: datetime
    
    def __str__(self) -> str:
        return f"1 BTC = ${self.usd:,.2f} USD / €{self.eur:,.2f} EUR"


@dataclass
class WalletSummary:
    """Data model representing wallet transaction summary"""
    address: str
    transactions: int
    total_received: float  # BTC
    total_sent: float      # BTC
    balance: float         # BTC
    fiat_price: Optional[FiatPrice] = None
    recent_txs: List[Transaction] = field(default_factory=list)
    
    @property
    def total_volume(self) -> float:
        """Total transaction volume = received + sent"""
        return self.total_received + self.total_sent
    
    @property
    def balance_usd(self) -> Optional[float]:
        """Current balance in USD"""
        if self.fiat_price:
            return self.balance * self.fiat_price.usd
        return None
    
    @property
    def balance_eur(self) -> Optional[float]:
        """Current balance in EUR"""
        if self.fiat_price:
            return self.balance * self.fiat_price.eur
        return None
    
    def __str__(self) -> str:
        """Formatted string representation of wallet summary"""
        output = [
            f"\n{'='*70}",
            f"₿  Bitcoin Wallet Summary",
            f"{'='*70}",
            f"Address:       {self.address}",
            f"Transactions:  {self.transactions:,}",
            f"{'-'*70}",
            f"Total Received: {self.total_received:>15,.8f} BTC",
            f"Total Sent:     {self.total_sent:>15,.8f} BTC",
            f"Total Volume:   {self.total_volume:>15,.8f} BTC",
            f"{'-'*70}",
            f"Current Balance: {self.balance:>14,.8f} BTC",
        ]
        
        # Add fiat values if available
        if self.fiat_price:
            output.extend([
                f"                 {self.balance_usd:>14,.2f} USD",
                f"                 {self.balance_eur:>14,.2f} EUR",
                f"",
                f"Market Price: {self.fiat_price}",
            ])
        
        # Add recent transactions
        if self.recent_txs:
            output.extend([
                f"{'='*70}",
                f"Recent Transactions (last {len(self.recent_txs)})",
                f"{'-'*70}",
            ])
            for tx in self.recent_txs:
                output.append(str(tx))
        
        output.append(f"{'='*70}")
        return "\n".join(output)


# ============================================================================
# API HANDLERS
# ============================================================================

class CoinGeckoAPI:
    """Handles CoinGecko price API requests"""
    
    BASE_URL = "https://api.coingecko.com/api/v3"
    
    def __init__(self):
        self.rate_limiter = RateLimiter(calls_per_minute=10)
    
    @timed_cache(seconds=300)  # Cache for 5 minutes
    @retry_with_backoff(max_attempts=3)
    def get_btc_price(self) -> Optional[FiatPrice]:
        """
        Fetch current BTC price in USD and EUR
        
        Returns:
            FiatPrice object or None on failure
        """
        self.rate_limiter.wait_if_needed()
        
        url = f"{self.BASE_URL}/simple/price"
        params = {
            'ids': 'bitcoin',
            'vs_currencies': 'usd,eur'
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'bitcoin' in data:
                return FiatPrice(
                    usd=data['bitcoin']['usd'],
                    eur=data['bitcoin']['eur'],
                    timestamp=datetime.now()
                )
            
            return None
            
        except requests.exceptions.RequestException as e:
            print(f"[-] CoinGecko API error: {e}")
            return None


class BlockchainAPI:
    """Handles communication with Blockchain.info API"""
    
    BASE_URL = "https://blockchain.info/rawaddr/"
    
    def __init__(self):
        self.rate_limiter = RateLimiter(calls_per_minute=5)
    
    @timed_cache(seconds=60)  # Cache for 1 minute
    @retry_with_backoff(max_attempts=3)
    def fetch_wallet_data(self, address: str, limit: int = 10) -> Optional[Dict[str, Any]]:
        """
        Fetch raw wallet data from Blockchain API
        
        Args:
            address: Bitcoin wallet address
            limit: Number of transactions to retrieve
            
        Returns:
            Parsed JSON response or None on failure
        """
        self.rate_limiter.wait_if_needed()
        
        url = f"{self.BASE_URL}{address}"
        params = {'limit': limit} if limit > 0 else {}
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'error' in data:
                print(f"[-] API Error: {data['error']}")
                return None
                
            return data
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                print(f"[-] Error: Wallet address not found")
            elif e.response.status_code == 429:
                print(f"[-] Error: Rate limit exceeded. Please wait and try again.")
            else:
                print(f"[-] HTTP Error ({e.response.status_code}): {e}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"[-] Network error: {e}")
            return None
        except ValueError as e:
            print(f"[-] Invalid API response: {e}")
            return None


# ============================================================================
# MAIN APPLICATION
# ============================================================================

class WalletExplorer:
    """Main application class for wallet exploration"""
    
    SATOSHIS_TO_BTC = 100_000_000
    
    def __init__(self):
        self.blockchain_api = BlockchainAPI()
        self.coingecko_api = CoinGeckoAPI()
    
    @staticmethod
    def print_banner() -> None:
        """Display application banner"""
        print("\n" + "="*60)
        print("₿  WalletWatch - Bitcoin Blockchain Explorer  ₿")
        print("="*60)
        print("Wallet analysis tool powered by Blockchain API")
        print("="*60 + "\n")
    
    @staticmethod
    def get_wallet_address() -> str:
        """Prompt user for valid wallet address"""
        while True:
            address = input("Enter Bitcoin wallet address: ").strip()
            if address and len(address) >= 26:  # Basic validation
                return address
            print("[-] Invalid address format. Please try again.\n")
    
    @staticmethod
    def get_transaction_limit() -> int:
        """Ask user how many transactions to display"""
        while True:
            try:
                limit = input("Show recent transactions? (0-50, default 10): ").strip()
                if not limit:
                    return 10
                limit_int = int(limit)
                if 0 <= limit_int <= 50:
                    return limit_int
                print("[-] Please enter a number between 0 and 50")
            except ValueError:
                print("[-] Please enter a valid number")
    
    def parse_transactions(self, raw_data: Dict[str, Any], limit: int) -> List[Transaction]:
        """
        Parse transaction data from API response
        
        Args:
            raw_data: Raw API response
            limit: Maximum number of transactions
            
        Returns:
            List of Transaction objects
        """
        if 'txs' not in raw_data or limit == 0:
            return []
        
        transactions = []
        address = raw_data['address']
        
        for tx in raw_data['txs'][:limit]:
            try:
                # Calculate net amount for this address
                amount = 0.0
                balance_after = 0.0
                
                # Sum inputs from this address
                for inp in tx.get('inputs', []):
                    if inp.get('prev_out', {}).get('addr') == address:
                        amount -= inp['prev_out']['value'] / self.SATOSHIS_TO_BTC
                
                # Sum outputs to this address
                for out in tx.get('out', []):
                    if out.get('addr') == address:
                        amount += out['value'] / self.SATOSHIS_TO_BTC
                        balance_after = out.get('value', 0) / self.SATOSHIS_TO_BTC
                
                # Only add if this address was involved
                if amount != 0:
                    transactions.append(Transaction(
                        hash=tx['hash'][:16] + "...",
                        time=datetime.fromtimestamp(tx['time']),
                        amount=amount,
                        balance_after=balance_after
                    ))
                    
            except (KeyError, TypeError, ValueError) as e:
                continue  # Skip malformed transactions
        
        return transactions
    
    def analyze_wallet(self, address: str, tx_limit: int = 10) -> Optional[WalletSummary]:
        """
        Analyze wallet and return structured summary
        
        Args:
            address: Bitcoin wallet address
            tx_limit: Number of recent transactions to fetch
            
        Returns:
            WalletSummary object or None on failure
        """
        print(f"\n[+] Fetching wallet data for: {address[:12]}...")
        raw_data = self.blockchain_api.fetch_wallet_data(address, limit=tx_limit)
        
        if not raw_data:
            return None
        
        print(f"[+] Fetching current BTC price...")
        fiat_price = self.coingecko_api.get_btc_price()
        
        if not fiat_price:
            print(f"[!] Warning: Could not fetch fiat prices")
        
        # Parse transactions
        transactions = self.parse_transactions(raw_data, tx_limit)
        
        # Convert satoshis to BTC
        return WalletSummary(
            address=address,
            transactions=raw_data.get('n_tx', 0),
            total_received=raw_data.get('total_received', 0) / self.SATOSHIS_TO_BTC,
            total_sent=raw_data.get('total_sent', 0) / self.SATOSHIS_TO_BTC,
            balance=raw_data.get('final_balance', 0) / self.SATOSHIS_TO_BTC,
            fiat_price=fiat_price,
            recent_txs=transactions
        )
    
    @staticmethod
    def continue_prompt() -> bool:
        """Prompt user to continue exploration"""
        while True:
            choice = input("\nAnalyze another wallet? (y/n): ").strip().lower()
            if choice in ('y', 'yes'):
                return True
            elif choice in ('n', 'no'):
                return False
            print("[-] Please enter 'y' or 'n'")
    
    def run(self) -> None:
        """Main application execution loop"""
        self.print_banner()
        
        while True:
            address = self.get_wallet_address()
            tx_limit = self.get_transaction_limit()
            
            summary = self.analyze_wallet(address, tx_limit)
            
            if summary:
                print(summary)
            else:
                print("\n[-] Failed to retrieve wallet information")
            
            if not self.continue_prompt():
                print("\n" + "="*70)
                print("Thank you for using WalletWatch!")
                print("="*70 + "\n")
                break


def main():
    """Application entry point"""
    try:
        explorer = WalletExplorer()
        explorer.run()
    except KeyboardInterrupt:
        print("\n\n[!] Operation cancelled by user. Exiting gracefully...")
    except Exception as e:
        print(f"\n[!] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("[+] Goodbye!")


if __name__ == "__main__":
    main()
