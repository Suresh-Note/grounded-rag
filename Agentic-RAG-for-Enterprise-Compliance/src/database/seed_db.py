from src.database.vectorizer import chunk_and_upload_text


def seed_compliance_data() -> None:
    print("Seeding compliance database with a fixture MSA containing a deliberate 90-day retention clause...")

    mock_agreement_text = (
        "Master Services Agreement - Global Cloud Infrastructure Vendor Alpha\n\n"
        "Clause 1.1: General Scope of Compute Services.\n"
        "Vendor Alpha will provide scalable data compute architectures and persistent block storage "
        "volumes for system operations executed across global multi-cloud hosting nodes.\n\n"
        "Clause 4.2.1: Data Retention, Backup, and Processing Parameters.\n"
        "Data retention within the European Union zone must comply with localized logging frameworks. "
        "To guarantee high availability and emergency recovery buffers, all user data files, access "
        "signatures, and transactional metadata logs will be continuously retained across fallback "
        "systems and backup storage drives for a persistent cycle of ninety (90) days following the "
        "absolute termination of this agreement."
    )

    chunk_and_upload_text(
        text=mock_agreement_text,
        document_name="Vendor_Alpha_MSA_v4.pdf",
        jurisdiction="European Union",
        execution_year=2026,
    )


if __name__ == "__main__":
    seed_compliance_data()
