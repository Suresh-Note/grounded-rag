import os

with open("src/api/main.py", "r", encoding="utf-8") as f:
    content = f.read()

# Add auto-init to startup event if not present
if "initialize_compliance_collection()" not in content:
    content = content.replace(
        'from src.database.pdf_processor import ingest_pdf_to_qdrant',
        'from src.database.pdf_processor import ingest_pdf_to_qdrant\nfrom src.database.qdrant_wrapper import initialize_compliance_collection'
    )
    content = content.replace(
        'async def on_startup() -> None:\n    logger.info("Aegis API started and ready to serve requests.")',
        'async def on_startup() -> None:\n    initialize_compliance_collection()\n    logger.info("Aegis API started and ready to serve requests.")'
    )
    with open("src/api/main.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("✅ Patched main.py with auto-initialization on startup!")
else:
    print("Main.py already patched.")
