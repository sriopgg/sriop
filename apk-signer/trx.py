
import logging
import requests
import time
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class TronAPIError(Exception):
    """Custom exception for TRON API errors"""
    pass

class TronAPI:
    """TRON blockchain API client"""
    
    def __init__(self):
        self.api_base = "https://api.trongrid.io"
        self.explorer_base = "https://apilist.tronscanapi.com/api"
        
    def get_transaction(self, tx_id: str) -> Optional[Dict[str, Any]]:
        """Get transaction details by transaction ID"""
        try:
            # Try TronGrid API first
            url = f"{self.api_base}/v1/transactions/{tx_id}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('data'):
                    return self._format_transaction(data['data'][0])
            
            # Fallback to TronScan API
            url = f"{self.explorer_base}/transaction-info"
            params = {'hash': tx_id}
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return self._format_tronscan_transaction(data)
            
            return None
            
        except requests.RequestException as e:
            logger.error(f"Network error getting transaction {tx_id}: {e}")
            raise TronAPIError(f"Network error: {e}")
        except Exception as e:
            logger.error(f"Error getting transaction {tx_id}: {e}")
            raise TronAPIError(f"Transaction lookup failed: {e}")
    
    def _format_transaction(self, tx_data: dict) -> Dict[str, Any]:
        """Format transaction data from TronGrid API"""
        try:
            contracts = tx_data.get('raw_data', {}).get('contract', [])
            if not contracts:
                return None
            
            contract = contracts[0]
            contract_type = contract.get('type')
            
            if contract_type == 'TransferContract':
                value = contract.get('parameter', {}).get('value', {})
                return {
                    'tx_id': tx_data.get('txID'),
                    'from_address': self._hex_to_base58(value.get('owner_address')),
                    'to_address': self._hex_to_base58(value.get('to_address')),
                    'amount': value.get('amount', 0) / 1_000_000,  # Convert from SUN to TRX
                    'confirmed': tx_data.get('ret', [{}])[0].get('contractRet') == 'SUCCESS',
                    'timestamp': tx_data.get('raw_data', {}).get('timestamp', 0),
                    'block_number': tx_data.get('blockNumber', 0)
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error formatting transaction: {e}")
            return None
    
    def _format_tronscan_transaction(self, tx_data: dict) -> Dict[str, Any]:
        """Format transaction data from TronScan API"""
        try:
            if not tx_data or 'contractRet' not in tx_data:
                return None
            
            transfers = tx_data.get('trc20TransferInfo', [])
            if transfers:
                transfer = transfers[0]
                return {
                    'tx_id': tx_data.get('hash'),
                    'from_address': transfer.get('from_address'),
                    'to_address': transfer.get('to_address'),
                    'amount': float(transfer.get('quant', 0)) / 1_000_000,
                    'confirmed': tx_data.get('confirmed', False),
                    'timestamp': tx_data.get('timestamp', 0),
                    'block_number': tx_data.get('block', 0)
                }
            
            # Check for regular TRX transfer
            if tx_data.get('contractType') == 1:  # TransferContract
                return {
                    'tx_id': tx_data.get('hash'),
                    'from_address': tx_data.get('ownerAddress'),
                    'to_address': tx_data.get('toAddress'),
                    'amount': tx_data.get('amount', 0) / 1_000_000,
                    'confirmed': tx_data.get('confirmed', False),
                    'timestamp': tx_data.get('timestamp', 0),
                    'block_number': tx_data.get('block', 0)
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error formatting TronScan transaction: {e}")
            return None
    
    def _hex_to_base58(self, hex_address: str) -> str:
        """Convert hex address to base58 (simplified)"""
        # This is a simplified implementation
        # In production, use proper TRON address conversion
        if not hex_address:
            return ""
        return hex_address  # Placeholder
    
    def validate_transaction(self, tx_id: str, expected_address: str, min_amount: float = 0) -> Dict[str, Any]:
        """Validate a transaction meets requirements"""
        try:
            tx_data = self.get_transaction(tx_id)
            
            if not tx_data:
                return {
                    'valid': False,
                    'error': 'Transaction not found',
                    'amount': 0,
                    'confirmed': False
                }
            
            # Check if transaction is confirmed
            if not tx_data['confirmed']:
                return {
                    'valid': False,
                    'error': 'Transaction not yet confirmed',
                    'amount': tx_data['amount'],
                    'confirmed': False
                }
            
            # Check destination address
            if tx_data['to_address'].lower() != expected_address.lower():
                return {
                    'valid': False,
                    'error': 'Transaction sent to wrong address',
                    'amount': tx_data['amount'],
                    'confirmed': True
                }
            
            # Check minimum amount
            if tx_data['amount'] < min_amount:
                return {
                    'valid': False,
                    'error': f'Amount too low. Minimum: {min_amount} TRX',
                    'amount': tx_data['amount'],
                    'confirmed': True
                }
            
            return {
                'valid': True,
                'amount': tx_data['amount'],
                'confirmed': True,
                'tx_data': tx_data
            }
            
        except Exception as e:
            logger.error(f"Error validating transaction {tx_id}: {e}")
            return {
                'valid': False,
                'error': f'Validation error: {str(e)}',
                'amount': 0,
                'confirmed': False
            }

# Global API instance
tron_api = TronAPI()

def verify_payment(tx_id: str, wallet_address: str, min_amount: float = 1.0) -> Dict[str, Any]:
    """Verify a TRX payment transaction"""
    return tron_api.validate_transaction(tx_id, wallet_address, min_amount)

def get_transaction_info(tx_id: str) -> Optional[Dict[str, Any]]:
    """Get transaction information"""
    return tron_api.get_transaction(tx_id)
