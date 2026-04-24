from feast import Entity

worker = Entity(name="worker", join_keys=["worker_id"])
location = Entity(name="location", join_keys=["city"])