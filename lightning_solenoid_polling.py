#!/usr/bin/env python3
"""
LNbits Payment Monitor - Polling Fallback Version
Uses specific payment status API for reliable payment detection
"""

import requests
import time
import json
import logging
from datetime import datetime, timedelta
import RPi.GPIO as GPIO
import sys

# Configuration
LNBITS_URL = "https://your-lnbits-server.com"  # Replace with your LNbits URL
WALLET_ID = "your-wallet-id"  # Replace with your wallet ID (from URL)
API_KEY = "your-invoice-key"  # Replace with your invoice/read key
RELAY_PIN = 18  # GPIO pin connected to relay (BCM numbering)
SOLENOID_DURATION = 5  # Duration in seconds to keep solenoid open
POLL_INTERVAL = 2  # How often to check payment status (seconds)
MIN_PAYMENT_AMOUNT = 1  # Minimum payment in sats to trigger (0 for any amount)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/pi/solenoid_controller.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class LightningPaymentMonitor:
    def __init__(self):
        self.pending_invoices = {}  # Track unpaid invoices {payment_hash: {amount, memo, created_time}}
        self.processed_payments = set()  # Track completed payments
        self.setup_gpio()
        self.headers = {
            "X-Api-Key": API_KEY,
            "Content-Type": "application/json"
        }
        
    def setup_gpio(self):
        """Initialize GPIO for relay control"""
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(RELAY_PIN, GPIO.OUT)
            GPIO.output(RELAY_PIN, GPIO.LOW)  # Relay off initially
            logger.info(f"GPIO initialized. Relay pin: {RELAY_PIN}")
        except Exception as e:
            logger.error(f"GPIO setup failed: {e}")
            sys.exit(1)
    
    def cleanup_gpio(self):
        """Clean up GPIO on exit"""
        GPIO.output(RELAY_PIN, GPIO.LOW)
        GPIO.cleanup()
        logger.info("GPIO cleaned up")
    
    def activate_solenoid(self, amount=0, payment_hash=""):
        """Activate solenoid for specified duration"""
        try:
            logger.info(f"💧 Activating solenoid for {SOLENOID_DURATION} seconds")
            logger.info(f"   Payment: {amount} sats, Hash: {payment_hash[:16]}...")
            GPIO.output(RELAY_PIN, GPIO.HIGH)  # Turn on relay
            time.sleep(SOLENOID_DURATION)
            GPIO.output(RELAY_PIN, GPIO.LOW)   # Turn off relay
            logger.info("✅ Solenoid deactivated")
        except Exception as e:
            logger.error(f"❌ Error controlling solenoid: {e}")
            GPIO.output(RELAY_PIN, GPIO.LOW)  # Ensure relay is off
    
    def get_recent_payments(self):
        """Get all payments to find new invoices"""
        try:
            url = f"{LNBITS_URL}/api/v1/payments"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                payments = response.json()
                return payments
            else:
                logger.error(f"❌ API request failed: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Network error: {e}")
            return None
    
    def check_specific_payment_status(self, payment_hash):
        """Check specific payment status using dedicated API endpoint"""
        try:
            url = f"{LNBITS_URL}/api/v1/payments/{payment_hash}"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                payment_data = response.json()
                is_paid = payment_data.get('paid', False)
                logger.debug(f"Payment {payment_hash[:16]}... status: {'PAID' if is_paid else 'PENDING'}")
                return is_paid, payment_data
            else:
                logger.error(f"❌ Payment check failed: {response.status_code}")
                return False, None
                
        except Exception as e:
            logger.error(f"❌ Error checking payment: {e}")
            return False, None
    
    def scan_for_new_invoices(self):
        """Scan for new unpaid invoices to monitor"""
        payments = self.get_recent_payments()
        if not payments:
            return
        
        new_invoices = 0
        
        for payment in payments:
            # Only look at incoming payments (positive amount)
            if payment.get('amount', 0) <= 0:
                continue
            
            payment_hash = payment.get('payment_hash', payment.get('checking_id', ''))
            amount = abs(payment.get('amount', 0)) // 1000  # Convert msat to sats
            memo = payment.get('memo', '')
            
            # Skip if we already know about this payment
            if payment_hash in self.pending_invoices or payment_hash in self.processed_payments:
                continue
            
            # Check minimum amount
            if MIN_PAYMENT_AMOUNT > 0 and amount < MIN_PAYMENT_AMOUNT:
                logger.debug(f"Skipping small invoice: {amount} sats")
                self.processed_payments.add(payment_hash)  # Mark as processed so we don't check again
                continue
            
            # Check current status using specific API
            is_paid, payment_data = self.check_specific_payment_status(payment_hash)
            
            if is_paid:
                # Payment is already completed - mark as processed but don't trigger solenoid for historical payments
                logger.debug(f"Marking historical payment as processed: {amount} sats")
                self.processed_payments.add(payment_hash)
            else:
                # Add to pending invoices to monitor
                self.pending_invoices[payment_hash] = {
                    'amount': amount,
                    'memo': memo,
                    'created_time': datetime.now()
                }
                logger.info(f"📄 New invoice detected: {amount} sats (monitoring for payment)")
                new_invoices += 1
        
        if new_invoices > 0:
            logger.info(f"👀 Now monitoring {len(self.pending_invoices)} pending invoices")
    
    def check_pending_payments(self):
        """Check status of all pending invoices"""
        if not self.pending_invoices:
            return
        
        completed_payments = []
        
        for payment_hash, invoice_data in self.pending_invoices.items():
            is_paid, payment_data = self.check_specific_payment_status(payment_hash)
            
            if is_paid:
                amount = invoice_data['amount']
                memo = invoice_data['memo']
                
                logger.info(f"🎉 PAYMENT COMPLETED!")
                logger.info(f"   Amount: {amount} sats")
                logger.info(f"   Memo: {memo[:50]}{'...' if len(memo) > 50 else ''}")
                logger.info(f"   Hash: {payment_hash[:16]}...")
                
                # Activate solenoid
                self.activate_solenoid(amount, payment_hash)
                
                # Mark as completed
                completed_payments.append(payment_hash)
                self.processed_payments.add(payment_hash)
        
        # Remove completed payments from pending list
        for payment_hash in completed_payments:
            del self.pending_invoices[payment_hash]
        
        # Clean up old pending invoices (older than 24 hours)
        cutoff_time = datetime.now() - timedelta(hours=24)
        expired_invoices = [
            payment_hash for payment_hash, data in self.pending_invoices.items()
            if data['created_time'] < cutoff_time
        ]
        
        for payment_hash in expired_invoices:
            logger.info(f"🗑️  Removing expired invoice: {payment_hash[:16]}...")
            del self.pending_invoices[payment_hash]
    
    def get_wallet_info(self):
        """Get wallet information for verification"""
        try:
            url = f"{LNBITS_URL}/api/v1/wallet"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"❌ Could not get wallet info: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting wallet info: {e}")
            return None
    
    def run(self):
        """Main monitoring loop"""
        logger.info("🚀 Starting Lightning Payment Monitor (Polling)")
        logger.info(f"📡 LNbits URL: {LNBITS_URL}")
        logger.info(f"⚡ Wallet ID: {WALLET_ID}")
        logger.info(f"🔄 Poll interval: {POLL_INTERVAL} seconds")
        logger.info(f"💰 Min payment: {MIN_PAYMENT_AMOUNT} sats")
        logger.info(f"⏱️  Solenoid duration: {SOLENOID_DURATION} seconds")
        
        # Verify wallet connection
        wallet_info = self.get_wallet_info()
        if wallet_info:
            balance_sats = wallet_info.get('balance', 0) // 1000
            wallet_name = wallet_info.get('name', 'Unknown')
            logger.info(f"✅ Connected to wallet: {wallet_name}")
            logger.info(f"💳 Current balance: {balance_sats} sats")
        else:
            logger.error("❌ Could not verify wallet connection")
            return
        
        logger.info("👀 Monitoring for payments... (Ctrl+C to stop)")
        
        # Initial scan for existing invoices (mark historical payments as processed)
        logger.info("🔍 Scanning existing payments (marking historical as processed)...")
        self.scan_for_new_invoices()
        
        if self.processed_payments:
            logger.info(f"📚 Marked {len(self.processed_payments)} historical payments as processed")
        
        logger.info("🎯 Ready to detect NEW payments only!")
        logger.info("💰 Send a Lightning payment to test the system")
        
        try:
            while True:
                # Check for new invoices
                self.scan_for_new_invoices()
                
                # Check status of pending invoices
                self.check_pending_payments()
                
                # Show status every 30 seconds
                if int(time.time()) % 30 == 0:
                    pending_count = len(self.pending_invoices)
                    if pending_count > 0:
                        logger.info(f"📊 Status: {pending_count} invoices pending payment")
                
                time.sleep(POLL_INTERVAL)
                
        except KeyboardInterrupt:
            logger.info("🛑 Shutting down...")
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
        finally:
            self.cleanup_gpio()

def main():
    # Verify configuration
    missing_config = []
    
    if LNBITS_URL == "https://your-lnbits-server.com":
        missing_config.append("LNBITS_URL")
    
    if API_KEY == "your-invoice-key":
        missing_config.append("API_KEY")
    
    if WALLET_ID == "your-wallet-id":
        missing_config.append("WALLET_ID")
    
    if missing_config:
        print("❌ ERROR: Please configure the following in the script:")
        for item in missing_config:
            print(f"   - {item}")
        print("\nEdit the configuration section at the top of this file.")
        sys.exit(1)
    
    # Create and run monitor
    monitor = LightningPaymentMonitor()
    monitor.run()

if __name__ == "__main__":
    main()
