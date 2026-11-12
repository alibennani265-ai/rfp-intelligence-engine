from fastapi.testclient import TestClient
from rfp_engine.api.main import app


def run_e2e_audit() -> None:
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200, f"Health check failed: {health.text}"
    print("[OK] 1/3 - Endpoint /health opérationnel")

    ingest = client.post("/ingest-past-studies")
    assert ingest.status_code == 200, f"Ingest failed: {ingest.text}"
    print(f"[OK] 2/3 - Ingestion études passées : {ingest.json()['message']}")

    with open("data/test_cctp_airbus.pdf", "rb") as pdf_file:
        upload = client.post(
            "/upload",
            files={"file": ("test_cctp_airbus.pdf", pdf_file, "application/pdf")},
        )
    assert upload.status_code == 200, f"Upload failed: {upload.text}"
    print(f"[OK] 3/3 - Upload & indexation CCTP : {upload.json()['total_requirements']} blocs extraits")


if __name__ == "__main__":
    run_e2e_audit()
