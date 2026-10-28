from rfp_engine.ingestion.parser import RFPParser


def main():
    # S'assure que ton fichier PDF dans data/ s'appelle sample_rfp.pdf
    pdf_path = "data/sample_rfp.pdf"
    parser = RFPParser(pdf_path)
    requirements = parser.parse()

    print(f"\n--- {len(requirements)} EXIGENCES DÉTECTÉES ---")
    for req in requirements[:10]:
        print(f"[{req.requirement_id}] ({req.section}) -> {req.text}")


if __name__ == "__main__":
    main()