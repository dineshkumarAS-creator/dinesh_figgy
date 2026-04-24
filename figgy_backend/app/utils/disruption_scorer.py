from dataclasses import dataclass
from typing import List, Dict

@dataclass
class ZoneRiskResult:
    zone_id: str
    risk_score: float        # 0–100
    risk_label: str          # "Safe" | "Caution" | "Avoid"
    confidence: float        # 0.0–1.0
    primary_signal: str      # dominant signal e.g. "rain" | "protest" | "none"
    alert_text: str          # e.g. "Rain active in T Nagar · Zone C is clear"

class DisruptionScorer:
    WEIGHTS = {"weather": 0.35, "govt": 0.30, "news": 0.25, "social": 0.10}
    THRESHOLDS = {"safe": 30, "caution": 65}  # below 30=Safe, 30-65=Caution, above=Avoid

    def score(self, zone_id: str, weather: Dict, govt: List[Dict], news: Dict, social: Dict) -> ZoneRiskResult:
        # Weather score
        rain_mm = weather.get("rain_mm", 0)
        wind_kmh = weather.get("wind_kmh", 0)
        if rain_mm > 10:
            weather_score = 80
        elif rain_mm > 5:
            weather_score = 50
        elif rain_mm > 0:
            weather_score = 20
        else:
            weather_score = 0
        if wind_kmh > 60:
            weather_score = min(weather_score + 20, 100)

        # Govt score
        govt_score = 0
        for alert in govt:
            if alert.get("active"):
                sev = alert.get("severity", "low")
                if sev == "high":
                    govt_score = max(govt_score, 90)
                elif sev == "medium":
                    govt_score = max(govt_score, 60)
                elif sev == "low":
                    govt_score = max(govt_score, 30)

        # News score
        keyword_hits = news.get("keyword_hits", 0)
        if keyword_hits >= 3:
            news_score = 80
        elif keyword_hits >= 1:
            news_score = 45
        else:
            news_score = 0

        # Social score
        spike_score = social.get("spike_score", 0.0)
        social_score = spike_score * 100

        # Weighted total
        weighted = {
            "weather": self.WEIGHTS["weather"] * weather_score,
            "govt": self.WEIGHTS["govt"] * govt_score,
            "news": self.WEIGHTS["news"] * news_score,
            "social": self.WEIGHTS["social"] * social_score,
        }
        risk_score = sum(weighted.values())
        risk_score = max(0, min(risk_score, 100))

        # Primary signal
        primary_signal = max(weighted, key=weighted.get)
        if weighted[primary_signal] == 0:
            primary_signal = "none"

        # Risk label
        if risk_score < self.THRESHOLDS["safe"]:
            risk_label = "Safe"
        elif risk_score < self.THRESHOLDS["caution"]:
            risk_label = "Caution"
        else:
            risk_label = "Avoid"

        # Confidence
        fallback_count = 0
        if weather.get("condition", "unknown") == "unknown":
            fallback_count += 1
        if not govt:
            fallback_count += 1
        if news.get("top_headline", "") == "":
            fallback_count += 1
        if social.get("spike_score", 0.0) == 0.0:
            fallback_count += 1
        confidence = 1.0 - (fallback_count / 4)

        # Alert text
        if primary_signal == "weather" and weather_score > 0:
            alert_text = f"{weather.get('condition', '').capitalize()} active in {zone_id}"
        elif primary_signal == "govt" and govt_score > 0:
            alert_types = [a["type"] for a in govt if a.get("active")]
            alert_text = f"{'/'.join(alert_types).capitalize()} alert in {zone_id}"
        elif primary_signal == "news" and news_score > 0:
            alert_text = news.get("top_headline", "")
        elif primary_signal == "social" and social_score > 0:
            alert_text = f"Social spike detected in {zone_id}"
        else:
            alert_text = f"Zone {zone_id} is clear"

        return ZoneRiskResult(
            zone_id=zone_id,
            risk_score=risk_score,
            risk_label=risk_label,
            confidence=confidence,
            primary_signal=primary_signal if primary_signal != "none" else "none",
            alert_text=alert_text
        )
