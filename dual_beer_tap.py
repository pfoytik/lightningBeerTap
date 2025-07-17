#!/usr/bin/env python3
"""
LNbits Dual Wallet Payment Monitor
Monitors two different wallets and controls two separate taps/solenoids
"""

import requests
import time
import json
import logging
from datetime import datetime, timedelta, timezone
import RPi.GPIO as GPIO
import sys
from dateutil import parser as date_parser

# Wallet 1 Configuration
WALLET_1_CONFIG = {
    "name": "Wallet 1",
    "lnbits_url": "https://your-lnbits-server.com",
    "wallet_id": "your-wallet-1-id",
    "api_key": "your-wallet-1-api-key",
    "relay_pin": 18,  # GPIO pin for first solenoid
    "min_payment_amount": 1,  # Minimum sats to trigger
    "sats_per_second": 10,    # Pour rate
    "max_pour_duration": 10,  # Safety cap
    "default_duration": 5     # Fallback duration
}

# Wallet 2 Configuration
WALLET_2_CONFIG = {
    "name": "Wallet 2", 
    "lnbits_url": "https://your-lnbits-server.com",  # Can be same or different server
    "wallet_id": "your-wallet-2-id",
    "api_key": "your-wallet-2-api-key", 
    "relay_pin": 19,  # GPIO pin for second solenoid
    "min_payment_amount": 5,  # Different minimum (example: premium tap)
    "sats_per_second": 15,    # Different pour rate
    "max_pour_duration": 15,  # Different max duration
    "default_duration": 7     # Different fallback
}

# General Configuration
POLL_INTERVAL = 1  # How often to check payment status (seconds)
LOOKBACK_MINUTES = 2  # How far back to look for recent payments

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/pi/dual_wallet_monitor.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class DualWalletPaymentMonitor:
    def __init__(self):
        self.wallets = [WALLET_1_CONFIG, WALLET_2_CONFIG]
        self.wallet_states = {}  # Store state for each wallet
        self.setup_gpio()
        self.setup_wallet_states()
        
    def setup_gpio(self):
        """Initialize GPIO for both relay controls"""
        try:
            GPIO.setmode(GPIO.BCM)
            
            # Setup both relay pins
            for wallet in self.wallets:
                pin = wallet['relay_pin']
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, GPIO.LOW)  # Relay off initially
                logger.info(f"GPIO initialized for {wallet['name']}: Pin {pin}")
                
        except Exception as e:
            logger.error(f"GPIO setup failed: {e}")
            sys.exit(1)
    
    def setup_wallet_states(self):
        """Initialize tracking state for each wallet"""
        for wallet in self.wallets:
            wallet_id = wallet['wallet_id']
            self.wallet_states[wallet_id] = {
                'pending_invoices': {},
                'processed_payments': set(),
                'last_check_time': datetime.now(timezone.utc) - timedelta(minutes=LOOKBACK_MINUTES),
                'headers': {
                    "X-Api-Key": wallet['api_key'],
                    "Content-Type": "application/json"
                }
            }
    
    def cleanup_gpio(self):
        """Clean up GPIO on exit"""
        try:
            # Turn off all relays
            for wallet in self.wallets:
                GPIO.output(wallet['relay_pin'], GPIO.LOW)
            GPIO.cleanup()
            logger.info("GPIO cleaned up")
        except:
            pass
    
    def calculate_pour_duration(self, amount_sats, wallet_config):
        """Calculate pour duration based on payment amount and wallet config"""
        sats_per_second = wallet_config['sats_per_second']
        max_duration = wallet_config['max_pour_duration']
        default_duration = wallet_config['default_duration']
        
        if sats_per_second <= 0:
            return default_duration
        
        calculated_duration = amount_sats / sats_per_second
        duration = min(calculated_duration, max_duration)
        duration = max(duration, 0.5)
        
        return round(duration, 1)
    
    def activate_solenoid(self, amount=0, payment_hash="", wallet_config=None):
        """Activate solenoid for calculated duration based on payment amount"""
        if not wallet_config:
            logger.error("No wallet config provided for solenoid activation")
            return
            
        try:
            pour_duration = self.calculate_pour_duration(amount, wallet_config)
            relay_pin = wallet_config['relay_pin']
            wallet_name = wallet_config['name']
            
            logger.info(f"💧 {wallet_name} payment received: {amount} sats")
            logger.info(f"⏱️  Calculated pour duration: {pour_duration} seconds")
            logger.info(f"🚿 Activating {wallet_name} solenoid (Pin {relay_pin})...")
            logger.info(f"   Hash: {payment_hash[:16]}...")
            
            GPIO.output(relay_pin, GPIO.HIGH)  # Turn on relay
            time.sleep(pour_duration)
            
        except Exception as e:
            logger.error(f"❌ Error controlling {wallet_name} solenoid: {e}")
        finally:
            # Always ensure relay is turned off
            if wallet_config:
                GPIO.output(wallet_config['relay_pin'], GPIO.LOW)
                logger.info(f"✅ {wallet_config['name']} solenoid deactivated after {pour_duration}s")
    
    def parse_payment_time(self, time_str):
        """Parse payment timestamp from various formats and ensure timezone awareness"""
        if not time_str:
            return None
        
        try:
            # Try different common formats
            formats = [
                "%Y-%m-%dT%H:%M:%S.%fZ",  # ISO with microseconds
                "%Y-%m-%dT%H:%M:%SZ",     # ISO without microseconds
                "%Y-%m-%dT%H:%M:%S.%f",   # ISO with microseconds, no Z
                "%Y-%m-%dT%H:%M:%S",      # ISO without microseconds, no Z
                "%Y-%m-%d %H:%M:%S",      # Simple format
            ]
            
            parsed_time = None
            
            for fmt in formats:
                try:
                    parsed_time = datetime.strptime(time_str, fmt)
                    break
                except ValueError:
                    continue
            
            # If none of the above work, try dateutil parser
            if not parsed_time:
                parsed_time = date_parser.parse(time_str)
            
            # Ensure timezone awareness
            if parsed_time.tzinfo is None:
                # If no timezone info, assume UTC
                parsed_time = parsed_time.replace(tzinfo=timezone.utc)
            
            return parsed_time
            
        except Exception as e:
            logger.debug(f"Could not parse time '{time_str}': {e}")
            return None
    
    def get_recent_payments(self, wallet_config, wallet_state):
        """Get all payments for a specific wallet"""
        try:
            url = f"{wallet_config['lnbits_url']}/api/v1/payments"
            response = requests.get(url, headers=wallet_state['headers'], timeout=10)
            
            if response.status_code == 200:
                payments = response.json()
                return payments
            else:
                logger.error(f"❌ {wallet_config['name']} API request failed: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ {wallet_config['name']} network error: {e}")
            return None
    
    def scan_for_recent_payments(self, wallet_config, wallet_state):
        """Scan for payments made since last check for specific wallet"""
        payments = self.get_recent_payments(wallet_config, wallet_state)
        if not payments:
            return
        
        current_time = datetime.now(timezone.utc)
        recent_payments_found = 0
        wallet_name = wallet_config['name']
        
        for payment in payments:
            # Only look at incoming payments (positive amount)
            amount = payment.get('amount', 0)
            if amount <= 0:
                continue
            
            payment_hash = payment.get('payment_hash', payment.get('checking_id', ''))
            amount_sats = abs(amount) // 1000  # Convert msat to sats
            memo = payment.get('memo', '')
            
            # Skip if already processed
            if payment_hash in wallet_state['processed_payments']:
                continue
            
            # Check minimum amount for this wallet
            if wallet_config['min_payment_amount'] > 0 and amount_sats < wallet_config['min_payment_amount']:
                logger.debug(f"{wallet_name}: Skipping small payment: {amount_sats} sats (min: {wallet_config['min_payment_amount']})")
                wallet_state['processed_payments'].add(payment_hash)
                continue
            
            # Parse payment timestamp
            payment_time = None
            for time_field in ['time', 'created_at', 'paid_at', 'date']:
                time_str = payment.get(time_field)
                if time_str:
                    payment_time = self.parse_payment_time(time_str)
                    if payment_time:
                        logger.debug(f"{wallet_name}: Found timestamp in field '{time_field}': {payment_time}")
                        break
            
            if not payment_time:
                logger.debug(f"{wallet_name}: No timestamp found for payment {payment_hash[:16]}... Available fields: {list(payment.keys())}")
                continue
            
            # Only process payments newer than last check
            if payment_time >= wallet_state['last_check_time']:
                # Check if payment is completed
                is_paid = payment.get('paid', False)
                
                if is_paid:
                    logger.info(f"🎉 {wallet_name} RECENT PAYMENT DETECTED!")
                    logger.info(f"   Amount: {amount_sats} sats")
                    logger.info(f"   Time: {payment_time}")
                    logger.info(f"   Memo: {memo[:50]}{'...' if len(memo) > 50 else ''}")
                    logger.info(f"   Hash: {payment_hash[:16]}...")
                    
                    # Activate solenoid for this wallet
                    self.activate_solenoid(amount_sats, payment_hash, wallet_config)
                    
                    # Mark as processed
                    wallet_state['processed_payments'].add(payment_hash)
                    recent_payments_found += 1
                else:
                    # Payment is recent but not paid yet - add to pending
                    if payment_hash not in wallet_state['pending_invoices']:
                        wallet_state['pending_invoices'][payment_hash] = {
                            'amount': amount_sats,
                            'memo': memo,
                            'created_time': payment_time
                        }
                        logger.info(f"📄 {wallet_name}: Recent unpaid invoice: {amount_sats} sats")
            else:
                logger.debug(f"{wallet_name}: Payment too old: {payment_time} < {wallet_state['last_check_time']}")
        
        if recent_payments_found > 0:
            logger.info(f"✨ {wallet_name}: Found {recent_payments_found} recent payments")
        
        # Update last check time
        wallet_state['last_check_time'] = current_time
    
    def check_specific_payment_status(self, payment_hash, wallet_config, wallet_state):
        """Check specific payment status using dedicated API endpoint"""
        try:
            url = f"{wallet_config['lnbits_url']}/api/v1/payments/{payment_hash}"
            response = requests.get(url, headers=wallet_state['headers'], timeout=10)
            
            if response.status_code == 200:
                payment_data = response.json()
                is_paid = payment_data.get('paid', False)
                logger.debug(f"{wallet_config['name']}: Payment {payment_hash[:16]}... status: {'PAID' if is_paid else 'PENDING'}")
                return is_paid, payment_data
            else:
                logger.error(f"❌ {wallet_config['name']}: Payment check failed: {response.status_code}")
                return False, None
                
        except Exception as e:
            logger.error(f"❌ {wallet_config['name']}: Error checking payment: {e}")
            return False, None
    
    def check_pending_payments(self, wallet_config, wallet_state):
        """Check status of pending invoices for specific wallet"""
        if not wallet_state['pending_invoices']:
            return
        
        completed_payments = []
        wallet_name = wallet_config['name']
        
        for payment_hash, invoice_data in wallet_state['pending_invoices'].items():
            is_paid, payment_data = self.check_specific_payment_status(payment_hash, wallet_config, wallet_state)
            
            if is_paid:
                amount = invoice_data['amount']
                memo = invoice_data['memo']
                
                logger.info(f"🎉 {wallet_name} PENDING PAYMENT COMPLETED!")
                logger.info(f"   Amount: {amount} sats")
                logger.info(f"   Memo: {memo[:50]}{'...' if len(memo) > 50 else ''}")
                logger.info(f"   Hash: {payment_hash[:16]}...")
                
                # Activate solenoid
                self.activate_solenoid(amount, payment_hash, wallet_config)
                
                # Mark as completed
                completed_payments.append(payment_hash)
                wallet_state['processed_payments'].add(payment_hash)
        
        # Remove completed payments from pending list
        for payment_hash in completed_payments:
            del wallet_state['pending_invoices'][payment_hash]
        
        # Clean up old pending invoices (older than 24 hours)
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
        expired_invoices = [
            payment_hash for payment_hash, data in wallet_state['pending_invoices'].items()
            if data['created_time'] < cutoff_time
        ]
        
        for payment_hash in expired_invoices:
            logger.info(f"🗑️  {wallet_name}: Removing expired invoice: {payment_hash[:16]}...")
            del wallet_state['pending_invoices'][payment_hash]
    
    def cleanup_old_processed_payments(self):
        """Clean up old processed payments to prevent memory leak"""
        for wallet_id, wallet_state in self.wallet_states.items():
            if len(wallet_state['processed_payments']) > 1000:  # Arbitrary limit
                logger.info(f"🧹 Cleaning up old processed payments for wallet {wallet_id}...")
                # Convert to list, keep last 500
                old_payments = list(wallet_state['processed_payments'])
                wallet_state['processed_payments'] = set(old_payments[-500:])
    
    def get_wallet_info(self, wallet_config, wallet_state):
        """Get wallet information for verification"""
        try:
            url = f"{wallet_config['lnbits_url']}/api/v1/wallet"
            response = requests.get(url, headers=wallet_state['headers'], timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"❌ {wallet_config['name']}: Could not get wallet info: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ {wallet_config['name']}: Error getting wallet info: {e}")
            return None
    
    def run(self):
        """Main monitoring loop"""
        logger.info("🚀 Starting Dual Wallet Lightning Payment Monitor")
        logger.info(f"🔄 Poll interval: {POLL_INTERVAL} seconds")
        logger.info(f"🕐 Lookback time: {LOOKBACK_MINUTES} minutes")
        
        # Verify wallet connections
        for wallet_config in self.wallets:
            wallet_state = self.wallet_states[wallet_config['wallet_id']]
            wallet_info = self.get_wallet_info(wallet_config, wallet_state)
            
            if wallet_info:
                balance_sats = wallet_info.get('balance', 0) // 1000
                wallet_name = wallet_info.get('name', wallet_config['name'])
                logger.info(f"✅ {wallet_config['name']} connected: {wallet_name}")
                logger.info(f"💳 {wallet_config['name']} balance: {balance_sats} sats")
                logger.info(f"🔧 {wallet_config['name']} config: Pin {wallet_config['relay_pin']}, Min {wallet_config['min_payment_amount']} sats, {wallet_config['sats_per_second']} sats/sec")
            else:
                logger.error(f"❌ Could not verify {wallet_config['name']} connection")
                return
        
        logger.info("👀 Monitoring both wallets for payments... (Ctrl+C to stop)")
        logger.info("⚡ This version catches BOTH fast internal AND slow external payments!")
        logger.info("💰 Send Lightning payments to either wallet to test the system")
        
        cleanup_counter = 0
        
        try:
            while True:
                # Process each wallet
                for wallet_config in self.wallets:
                    wallet_state = self.wallet_states[wallet_config['wallet_id']]
                    
                    # Check for recent payments (catches fast internal payments)
                    self.scan_for_recent_payments(wallet_config, wallet_state)
                    
                    # Check status of pending invoices (for slow external payments)  
                    self.check_pending_payments(wallet_config, wallet_state)
                
                # Periodic cleanup
                cleanup_counter += 1
                if cleanup_counter % 300 == 0:  # Every 5 minutes
                    self.cleanup_old_processed_payments()
                
                # Show status every 30 seconds
                if cleanup_counter % 30 == 0:
                    for wallet_config in self.wallets:
                        wallet_state = self.wallet_states[wallet_config['wallet_id']]
                        pending_count = len(wallet_state['pending_invoices'])
                        processed_count = len(wallet_state['processed_payments'])
                        logger.info(f"📊 {wallet_config['name']}: {pending_count} pending, {processed_count} processed")
                
                time.sleep(POLL_INTERVAL)
                
        except KeyboardInterrupt:
            logger.info("🛑 Shutting down...")
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
        finally:
            self.cleanup_gpio()

def main():
    # Verify configuration for both wallets
    missing_config = []
    
    for i, wallet in enumerate([WALLET_1_CONFIG, WALLET_2_CONFIG], 1):
        if wallet['lnbits_url'] == "https://your-lnbits-server.com":
            missing_config.append(f"WALLET_{i}_CONFIG['lnbits_url']")
        
        if wallet['api_key'] == f"your-wallet-{i}-api-key":
            missing_config.append(f"WALLET_{i}_CONFIG['api_key']")
        
        if wallet['wallet_id'] == f"your-wallet-{i}-id":
            missing_config.append(f"WALLET_{i}_CONFIG['wallet_id']")
    
    # Check for GPIO pin conflicts
    pins = [WALLET_1_CONFIG['relay_pin'], WALLET_2_CONFIG['relay_pin']]
    if pins[0] == pins[1]:
        missing_config.append("GPIO pins must be different for each wallet")
    
    if missing_config:
        print("❌ ERROR: Please configure the following:")
        for item in missing_config:
            print(f"   - {item}")
        print("\nEdit the configuration section at the top of this file.")
        sys.exit(1)
    
    # Create and run monitor
    monitor = DualWalletPaymentMonitor()
    monitor.run()

if __name__ == "__main__":
    main()