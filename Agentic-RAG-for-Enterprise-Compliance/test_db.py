from src.database.qdrant_wrapper import initialize_compliance_collection

if __name__ == "__main__":
    print("Connecting to Qdrant and initializing the compliance collection...")
    initialize_compliance_collection()
