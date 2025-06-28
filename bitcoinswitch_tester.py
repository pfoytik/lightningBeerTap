#!/usr/bin/env python3
"""
LNbits Payment Status API Tester for Ubuntu
Test the specific payment status API before deploying to Raspberry Pi
"""

import requests
import json
import time
from datetime import datetime, timedelta
import sys
import asyncio

# Configuration - Update these with your actual values
LNBITS_URL = "https://your-lnbits-server.com"  # Replace with your LNbits URL
WALLET_ID = "your-wallet-id"                   # Replace with your wallet ID
API_KEY = "your-invoice-key"                   # Replace with your invoice/read key

class LNbitsPaymentTester:
    def __init__(self):
        self.headers = {
            "X-Api-Key": API_KEY,
            "Content-Type": "application/json"
        }
        print("LNbits Payment Status API Tester")
        print("=" * 50)
        print(f"LNbits URL: {LNBITS_URL}")
        print(f"Wallet ID: {WALLET_ID}")
        print("=" * 50)
    
    def test_connection(self):
        """Test basic connection to LNbits wallet"""
        print("\n1. Testing LNbits wallet connection...")
        try:
            url = f"{LNBITS_URL}/api/v1/wallet"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                balance_sats = data.get('balance', 0) // 1000
                print(f"✅ Connection successful!")
                print(f"   Wallet Name: {data.get('name', 'Unknown')}")
                print(f"   Wallet ID: {data.get('id', 'Unknown')}")
                print(f"   Balance: {balance_sats} sats")
                return True
            else:
                print(f"❌ Connection failed: HTTP {response.status_code}")
                if response.status_code == 401:
                    print("   Check your API key - it might be wrong or expired")
                elif response.status_code == 404:
                    print("   Check your LNbits URL and wallet ID")
                print(f"   Response: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error: {e}")
            return False
    
    def test_payments_list_api(self):
        """Test payments list API endpoint"""
        print("\n2. Testing payments list API...")
        try:
            url = f"{LNBITS_URL}/api/v1/payments"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                payments = response.json()
                print(f"✅ Payments list API working!")
                print(f"   Found {len(payments)} total payments")
                
                # Analyze payment types - be careful about paid status here
                incoming_all = [p for p in payments if p.get('amount', 0) > 0]
                outgoing = [p for p in payments if p.get('amount', 0) < 0]
                
                print(f"   Incoming transactions: {len(incoming_all)} (includes unpaid invoices)")
                print(f"   Outgoing payments: {len(outgoing)}")
                
                # Show recent incoming transactions
                if incoming_all:
                    print(f"\n   Recent incoming transactions:")
                    for i, payment in enumerate(incoming_all[:5]):
                        amount = payment.get('amount', 0) // 1000
                        memo = payment.get('memo', 'No memo')[:30]
                        payment_hash = payment.get('payment_hash', 'Unknown')[:16]
                        # Note: Don't trust the 'paid' status from this API
                        paid_status = payment.get('paid', False)
                        status_text = f"API says: {'PAID' if paid_status else 'PENDING'}"
                        print(f"     {i+1}. {amount} sats - {memo} - {payment_hash}... - {status_text}")
                
                return payments
            else:
                print(f"❌ Payments API failed: HTTP {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error: {e}")
            return None
    
    def test_specific_payment_api(self, payment_hash):
        """Test the specific payment status API"""
        print(f"\n   Testing specific payment API for {payment_hash[:16]}...")
        try:
            url = f"{LNBITS_URL}/api/v1/payments/{payment_hash}"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                payment_data = response.json()
                is_paid = payment_data.get('paid', False)
                print(f"   ✅ Specific API result: {'✅ PAID' if is_paid else '⏳ PENDING'}")
                return is_paid, payment_data
            else:
                print(f"   ❌ Specific API failed: HTTP {response.status_code}")
                return None, None
                
        except Exception as e:
            print(f"   ❌ Error checking specific payment: {e}")
            return None, None
    
    def compare_api_results(self):
        """Compare results between payments list and specific payment APIs"""
        print("\n3. Comparing API results...")
        payments = self.test_payments_list_api()
        
        if not payments:
            return
        
        # Test specific API for recent incoming payments
        incoming_payments = [p for p in payments if p.get('amount', 0) > 0][:3]
        
        if not incoming_payments:
            print("   No incoming payments to test specific API")
            return
        
        print(f"\n   Comparing list API vs specific API for {len(incoming_payments)} payments:")
        
        for payment in incoming_payments:
            payment_hash = payment.get('payment_hash', '')
            amount = payment.get('amount', 0) // 1000
            list_api_paid = payment.get('paid', False)
            
            print(f"\n   Payment: {amount} sats ({payment_hash[:16]}...)")
            print(f"   List API says: {'✅ PAID' if list_api_paid else '⏳ PENDING'}")
            
            # Check with specific API
            specific_paid, specific_data = self.test_specific_payment_api(payment_hash)
            
            if specific_paid is not None:
                if list_api_paid == specific_paid:
                    print(f"   ✅ APIs agree: {'PAID' if specific_paid else 'PENDING'}")
                else:
                    print(f"   ⚠️  APIs disagree! List: {list_api_paid}, Specific: {specific_paid}")
                    print(f"       ➡️  Use specific API result: {specific_paid}")
    
    def create_test_invoice(self, amount_sats=10):
        """Create a test Lightning invoice"""
        print(f"\n4. Creating test invoice for {amount_sats} sats...")
        try:
            invoice_data = {
                "out": False,
                "amount": amount_sats,
                "memo": f"Test payment status API - {datetime.now().strftime('%H:%M:%S')}",
                "expiry": 3600  # 1 hour
            }
            
            url = f"{LNBITS_URL}/api/v1/payments"
            response = requests.post(url, headers=self.headers, json=invoice_data, timeout=10)
            
            if response.status_code == 201:
                invoice = response.json()
                payment_hash = invoice.get('payment_hash', '')
                
                print(f"✅ Test invoice created!")
                print(f"   Amount: {amount_sats} sats")
                print(f"   Memo: {invoice_data['memo']}")
                print(f"   Payment Hash: {payment_hash}")
                print(f"   \n📱 PAYMENT REQUEST:")
                print(f"   {invoice.get('payment_request', 'Not found')}")
                
                # Immediately test the specific payment API
                print(f"\n   Testing immediate status check...")
                is_paid, payment_data = self.test_specific_payment_api(payment_hash)
                if is_paid is not None:
                    print(f"   Status immediately after creation: {'✅ PAID' if is_paid else '⏳ PENDING (expected)'}")
                
                return invoice
            else:
                print(f"❌ Invoice creation failed: HTTP {response.status_code}")
                print(f"   Response: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error: {e}")
            return None
    
    def monitor_payment_status(self, payment_hash, duration=120):
        """Monitor specific payment hash for status changes"""
        print(f"\n5. Monitoring payment {payment_hash[:16]}... for {duration} seconds")
        print("   Pay the invoice above to see real-time status detection!")
        print("   Press Ctrl+C to stop monitoring early")
        
        start_time = time.time()
        last_status = None
        check_count = 0
        
        try:
            while time.time() - start_time < duration:
                check_count += 1
                is_paid, payment_data = self.test_specific_payment_api(payment_hash)
                
                if is_paid is not None:
                    current_status = "PAID" if is_paid else "PENDING"
                    
                    # Show status change
                    if current_status != last_status:
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        if current_status == "PAID":
                            print(f"   [{timestamp}] 🎉 PAYMENT STATUS CHANGED: {current_status}")
                            print(f"   💰 Payment confirmed! Solenoid would activate now!")
                            if payment_data:
                                amount = payment_data.get('amount', 0) // 1000
                                print(f"   💧 Triggering solenoid for {amount} sats payment")
                            break
                        else:
                            print(f"   [{timestamp}] Status: {current_status}")
                        
                        last_status = current_status
                    
                    # Show periodic status
                    if check_count % 10 == 0:
                        elapsed = int(time.time() - start_time)
                        remaining = duration - elapsed
                        print(f"   [{elapsed}s] Still {current_status.lower()}... ({remaining}s remaining, {check_count} checks)")
                
                time.sleep(2)  # Check every 2 seconds
                
        except KeyboardInterrupt:
            print("\n   Monitoring stopped by user")
        except Exception as e:
            print(f"\n   Monitoring error: {e}")
        
        print(f"\n   Monitoring complete! ({check_count} status checks performed)")
    
    def test_websocket_connection(self):
        """Test WebSocket connection"""
        print("\n6. Testing WebSocket connection...")
        
        try:
            import websockets
            
            # Build WebSocket URL
            ws_url = LNBITS_URL.replace('https://', 'wss://').replace('http://', 'ws://')
            websocket_url = f"{ws_url}/api/v1/ws/{API_KEY}"
            
            print(f"   WebSocket URL: {websocket_url}")
            
            async def test_ws():
                try:
                    print("   Attempting WebSocket connection...")
                    async with websockets.connect(websocket_url, ping_timeout=10) as websocket:
                        print("   ✅ WebSocket connected successfully!")
                        print("   Waiting for test message (5 seconds)...")
                        
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                            print(f"   📨 Received message: {message[:100]}...")
                            return True
                        except asyncio.TimeoutError:
                            print("   ⏰ No immediate messages (this is normal)")
                            return True
                            
                except Exception as e:
                    print(f"   ❌ WebSocket connection failed: {e}")
                    return False
            
            return asyncio.run(test_ws())
            
        except ImportError:
            print("   ⚠️  websockets library not installed")
            print("   Install with: pip3 install websockets")
            return False
        except Exception as e:
            print(f"   ❌ WebSocket test error: {e}")
            return False
    
    def run_full_test(self):
        """Run all tests in sequence"""
        print("Starting comprehensive payment status API test...\n")
        
        # Test 1: Basic connection
        if not self.test_connection():
            print("\n❌ FAILED: Cannot connect to LNbits wallet")
            return False
        
        # Test 2: Compare API results
        self.compare_api_results()
        
        # Test 3: WebSocket test
        self.test_websocket_connection()
        
        # Test 4: Create invoice and monitor
        print("\nChoose test invoice amount:")
        print("1. 10 sats (recommended)")
        print("2. 100 sats")
        print("3. Custom amount")
        print("4. Skip invoice test")
        
        try:
            choice = input("Enter choice (1-4): ").strip()
            
            if choice == "1":
                amount = 10
            elif choice == "2":
                amount = 100
            elif choice == "3":
                amount = int(input("Enter amount in sats: "))
            else:
                amount = 0
            
            if amount > 0:
                invoice = self.create_test_invoice(amount)
                
                if invoice:
                    payment_hash = invoice.get('payment_hash', '')
                    if payment_hash:
                        print(f"\nDo you want to monitor this payment for status changes? (y/n): ", end="")
                        if input().lower().startswith('y'):
                            self.monitor_payment_status(payment_hash)
        
        except (ValueError, KeyboardInterrupt):
            print("\nSkipping invoice test")
        
        print("\n🎉 All tests completed!")
        print("\n📋 Summary:")
        print("- Use the specific payment API (/api/v1/payments/<hash>) for reliable status")
        print("- The payments list API may not update 'paid' status reliably")
        print("- WebSocket provides real-time updates if available")
        print("- Your setup should work correctly with the new monitoring approach!")
        return True

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
        print("\nHow to get these values:")
        print("1. LNBITS_URL: Your LNbits server URL (e.g., https://legend.lnbits.com)")
        print("2. WALLET_ID: From your wallet URL (the ID after /wallet/)")
        print("3. API_KEY: Invoice/read key from wallet settings")
        sys.exit(1)
    
    # Create tester and run
    tester = LNbitsPaymentTester()
    
    print("\nChoose test mode:")
    print("1. Full test suite (recommended)")
    print("2. Quick connection test only")
    print("3. API comparison test only")
    print("4. Create invoice and monitor only")
    print("5. WebSocket test only")
    
    try:
        choice = input("\nEnter choice (1-5): ").strip()
        
        if choice == "1":
            tester.run_full_test()
        elif choice == "2":
            tester.test_connection()
        elif choice == "3":
            tester.test_connection()
            tester.compare_api_results()
        elif choice == "4":
            if tester.test_connection():
                amount = int(input("Enter amount in sats: ") or "10")
                invoice = tester.create_test_invoice(amount)
                if invoice:
                    payment_hash = invoice.get('payment_hash', '')
                    if payment_hash:
                        tester.monitor_payment_status(payment_hash)
        elif choice == "5":
            tester.test_websocket_connection()
        else:
            print("Invalid choice")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()
