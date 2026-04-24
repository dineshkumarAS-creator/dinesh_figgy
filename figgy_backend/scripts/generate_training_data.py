import os
import csv
import random

def generate_data():
    output_path = os.path.join(os.path.dirname(__file__), "training_data.csv")
    
    headers = ["avg_daily_earnings", "daily_hours", "zone_risk_score", "weekly_deliveries", "income_stability", "platform", "weekly_premium"]
    
    zones = {
        "North": 0.7,
        "South": 0.5,
        "East": 0.6,
        "West": 0.4,
        "Central": 0.8
    }

    data = []
    for _ in range(500):
        avg_daily = random.uniform(300, 2000)
        daily_hours = random.uniform(4, 14)
        zone_risk = random.choice(list(zones.values()))
        weekly_deliveries = random.uniform(50, 200)
        stability = random.uniform(0, 1)
        platform = random.choice([0, 1, 2])
        
        base_premium = avg_daily * 7 * 0.0015
        zone_adjustment = zone_risk * 15
        stability_adjustment = (1 - stability) * 10
        
        premium = base_premium + zone_adjustment + stability_adjustment
        premium = max(10, min(99, premium))
        
        data.append([
            round(avg_daily, 2),
            round(daily_hours, 1),
            zone_risk,
            int(weekly_deliveries),
            round(stability, 2),
            platform,
            round(premium, 2)
        ])
        
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(data)
        
    print(f"Generated 500 rows at {output_path}")

if __name__ == "__main__":
    generate_data()
