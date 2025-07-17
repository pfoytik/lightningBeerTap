# Example Configuration for Different Use Cases

# OPTION 1: Water vs Beer Setup
WALLET_1_CONFIG = {
    "name": "Water Tap",
    "lnbits_url": "https://your-lnbits-server.com",
    "wallet_id": "abc123-water-wallet-id",
    "api_key": "your-water-wallet-api-key",
    "relay_pin": 18,           # GPIO 18 for water solenoid
    "min_payment_amount": 1,   # 1 sat minimum for water
    "sats_per_second": 20,     # Fast pour: 20 sats = 1 second
    "max_pour_duration": 5,    # Max 5 seconds
    "default_duration": 2      # 2 second default
}

WALLET_2_CONFIG = {
    "name": "Beer Tap",
    "lnbits_url": "https://your-lnbits-server.com", 
    "wallet_id": "def456-beer-wallet-id",
    "api_key": "your-beer-wallet-api-key",
    "relay_pin": 19,           # GPIO 19 for beer solenoid
    "min_payment_amount": 10,  # 10 sats minimum for beer
    "sats_per_second": 5,      # Slow pour: 5 sats = 1 second
    "max_pour_duration": 20,   # Max 20 seconds
    "default_duration": 5      # 5 second default
}

# OPTION 2: Small vs Large Pour Setup
WALLET_1_CONFIG = {
    "name": "Small Pour",
    "lnbits_url": "https://your-lnbits-server.com",
    "wallet_id": "small-pour-wallet-id", 
    "api_key": "small-pour-api-key",
    "relay_pin": 18,
    "min_payment_amount": 1,   # 1-9 sats for small
    "sats_per_second": 50,     # Very fast pour
    "max_pour_duration": 3,    # Short max duration
    "default_duration": 1
}

WALLET_2_CONFIG = {
    "name": "Large Pour",
    "lnbits_url": "https://your-lnbits-server.com",
    "wallet_id": "large-pour-wallet-id",
    "api_key": "large-pour-api-key", 
    "relay_pin": 19,
    "min_payment_amount": 10,  # 10+ sats for large
    "sats_per_second": 10,     # Standard pour rate
    "max_pour_duration": 30,   # Long max duration
    "default_duration": 10
}

# OPTION 3: Two Different LNbits Servers
WALLET_1_CONFIG = {
    "name": "Server 1 Wallet",
    "lnbits_url": "https://server1.example.com", 
    "wallet_id": "wallet-on-server-1",
    "api_key": "server-1-api-key",
    "relay_pin": 18,
    "min_payment_amount": 1,
    "sats_per_second": 10,
    "max_pour_duration": 10,
    "default_duration": 5
}

WALLET_2_CONFIG = {
    "name": "Server 2 Wallet",
    "lnbits_url": "https://server2.example.com",  # Different server!
    "wallet_id": "wallet-on-server-2", 
    "api_key": "server-2-api-key",
    "relay_pin": 19,
    "min_payment_amount": 5,
    "sats_per_second": 15,
    "max_pour_duration": 15,
    "default_duration": 7
}