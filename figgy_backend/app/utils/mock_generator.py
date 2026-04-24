import random
import hashlib
from typing import Dict, Any

# Mock lists for deterministic choices
INDIAN_CITIES = ["Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai", "Kolkata", "Pune", "Jaipur"]
ZONES = ["North", "South", "East", "West", "Central"]

# 🛡️ HARDCODED IMMUTABLE PROFILES (Pure Demo Identity - Never Changes)
IMMUTABLE_PROFILES = {
    "7550080899": {
        "worker_id": "GS-OVVSRL",
        "swiggy_id": "7550080899",
        "name": "Rider_899",
        "phone": "7550080899",
        "platform": "Swiggy",
        "zone": "North",
        "income_category": "Medium",
        "suggested_premium": 20,
        "status": "Active",
        
        # 📈 TODAY'S PERFORMANCE (Matches UI Cards)
        "today_performance": {
            "earnings": 520,
            "active_hours": 5,
            "deliveries": 12
        },
        
        # 💳 BANKING DETAILS
        "bank_details": {
            "account_holder_name": "Rider_899",
            "bank_name": "State Bank of India",
            "account_number": "XXXX12345678",
            "ifsc_code": "SBIN0001234",
            "upi_id": "7550080899@okaxis"
        },
        
        # 🛡️ KYC & IDENTITY
        "kyc_details": {
            "aadhaar_number": "XXXX-XXXX-1234",
            "pan_number": "ABCDE1234F",
            "driving_license": "TN-1234567890",
            "vehicle_type": "Bike",
            "vehicle_number": "TN-10-AB-1234"
        },
        
        # 💰 HISTORICAL EARNINGS
        "earnings": {
            "avg_daily_earnings": 714,
            "weekly_earnings": 5000,
            "monthly_earnings": 22000,
            "total_earnings": 150000
        },
        
        # 🚀 WORK STATS
        "work_stats": {
            "daily_hours": 8,
            "weekly_deliveries": 100,
            "total_deliveries": 3200,
            "acceptance_rate": 92,
            "rating": 4.6
        },

        # 🎁 INCENTIVES
        "incentives": {
            "current_bonus": 500,
            "weekly_target": 120,
            "completed_target": 100,
            "surge_earnings": 300
        }
    }
}

# Official Partner Archive (Whitelisted IDs)
VALID_SWIGGY_IDS = list(IMMUTABLE_PROFILES.keys()) + ["SWG101", "SWG102", "dinesh_", "SWG777", "HACKER_123"]

def generate_worker_data(identifier: str) -> Dict[str, Any]:
    """Generates detailed mock data. Checks for Immutable profiles first."""
    
    # 🕵️ Check Primary Switch: Hardcoded profiles
    if identifier in IMMUTABLE_PROFILES:
        return IMMUTABLE_PROFILES[identifier]
        
    # if identifier not in VALID_SWIGGY_IDS:
    #     return None
        
    seed_hash = int(hashlib.md5(identifier.encode()).hexdigest(), 16)
    random.seed(seed_hash)

    last_three = identifier[-3:] if len(identifier) >= 3 else identifier
    name = f"Rider_{last_three}"
    if identifier == "dinesh_": name = "Dinesh Kumar"
    
    # 🍱 Full-Rich Dynamic Map for others
    return {
        "worker_id": f"GS-{identifier.upper()}",
        "swiggy_id": identifier,
        "name": name,
        "phone": f"9XXXXXX{last_three}" if identifier != "7550080899" else "7550080899",
        "email": f"{identifier.lower()}@figgy.app",
        "platform": "Swiggy",
        "zone": random.choice(ZONES),
        "city": random.choice(INDIAN_CITIES),
        "status": "Active",
        
        "today_performance": {
            "earnings": random.randint(300, 900),
            "active_hours": random.randint(3, 8),
            "deliveries": random.randint(5, 20)
        },
        
        "kyc_details": {
            "aadhaar_number": "XXXX-XXXX-1234",
            "pan_number": "ABCDE1234F",
            "driving_license": f"TN-{random.randint(10000000, 99999999)}",
            "vehicle_type": "Bike",
            "vehicle_number": f"MH-{random.randint(10, 99)}-AB-{random.randint(1000, 9999)}"
        },
        
        "bank_details": {
            "account_holder_name": name,
            "bank_name": "State Bank of India",
            "account_number": f"XXXX{random.randint(10000000, 99999999)}",
            "ifsc_code": "SBIN0001234",
            "upi_id": f"{identifier.lower()}@okaxis"
        },
        
        "earnings": {
            "avg_daily_earnings": random.randint(600, 1500),
            "weekly_earnings": random.randint(4000, 8000),
            "monthly_earnings": random.randint(18000, 32000),
            "total_earnings": random.randint(45000, 120000)
        },
        
        "work_stats": {
            "daily_hours": random.randint(6, 12),
            "weekly_deliveries": random.randint(80, 150),
            "total_deliveries": random.randint(800, 4500),
            "acceptance_rate": random.randint(85, 98),
            "rating": float(f"{random.uniform(4.2, 4.9):.1f}")
        },
        
        "incentives": {
            "current_bonus": random.choice([200, 500, 800]),
            "weekly_target": random.choice([100, 120, 150]),
            "completed_target": random.randint(60, 100),
            "surge_earnings": random.randint(100, 600)
        }
    }
