import os
import sys

# Force Python to look at the absolute root workspace first
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.database.qdrant_wrapper import initialize_compliance_collection

if __name__ == "__main__":
    print("Connecting to Qdrant and initializing the compliance collection...")
    initialize_compliance_collection()
