from pymongo import MongoClient
import sys

def test_conn():
    uri = "mongodb+srv://dinesh:dinesh%4012345@cluster0.aismgnj.mongodb.net/figgy?retryWrites=true&w=majority"
    print(f"Testing URI: {uri}")
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        # Force a connection
        info = client.server_info()
        print("Successfully connected to MongoDB Atlas!")
        print(f"Server Info: {info.get('version')}")
    except Exception as e:
        print(f"FAILED to connect: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_conn()
