from feast import FeatureView
from entities import worker, location

# Environmental FV
environmental_fv = FeatureView(
    name="environmental_fv",
    entities=[location],
    ttl=3600*24,  # 24h
    # features list
)

# Worker behaviour FV
worker_behaviour_fv = FeatureView(
    name="worker_behaviour_fv",
    entities=[worker],
    ttl=3600,  # 1h
)

# Income signals FV
income_signals_fv = FeatureView(
    name="income_signals_fv",
    entities=[worker],
    ttl=7200,  # 2h
)