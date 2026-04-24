class PhysicalLimits:
    @staticmethod
    def check_speed(speed_ms: float) -> bool:
        # 80 km/h = 22.22 m/s
        return speed_ms > 22.22

    @staticmethod
    def check_temperature(temp_c: float) -> bool:
        # Reasonable range for India
        return not (-10 <= temp_c <= 50)

    # Add more if needed