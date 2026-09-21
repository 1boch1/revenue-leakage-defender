from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def generate_invoice_pdf() -> Path:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(text="FATTURA", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    pdf.set_font("Helvetica", "", 11)
    pdf.cell(text="Numero: INV-2024-1042", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(text="Data emissione: 2024-06-15", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(text="Data scadenza: 2024-07-15", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(text="Termini di pagamento: 30 giorni", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(text="Fornitore:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(text="TechConsult S.r.l.", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(text="Via Roma 42, 20121 Milano", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(text="P.IVA: IT12345678901", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(text="Cliente:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(text="ACME Italia S.p.A.", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(text="Corso Vittorio Emanuele 100, 00186 Roma", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(text="P.IVA: IT98765432109", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(w=70, h=10, text="Descrizione", border=1)
    pdf.cell(w=25, h=10, text="Qty", border=1, align="C")
    pdf.cell(w=40, h=10, text="Prezzo Unit.", border=1, align="R")
    pdf.cell(w=40, h=10, text="Totale", border=1, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 10)
    rows = [
        ("Consulenza Senior", "10", "600,00 EUR", "6.000,00 EUR"),
        ("Sviluppo Software", "15", "450,00 EUR", "6.750,00 EUR"),
        ("Project Management", "5", "550,00 EUR", "2.750,00 EUR"),
        ("Formazione Team", "3", "400,00 EUR", "1.250,00 EUR"),
    ]
    for desc, qty, unit, total in rows:
        pdf.cell(w=70, h=8, text=desc, border=1)
        pdf.cell(w=25, h=8, text=qty, border=1, align="C")
        pdf.cell(w=40, h=8, text=unit, border=1, align="R")
        pdf.cell(w=40, h=8, text=total, border=1, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)

    pdf.set_font("Helvetica", "", 11)
    pdf.cell(w=135, h=8, text="Subtotale (imponibile):", align="R")
    pdf.cell(w=40, h=8, text="16.800,00 EUR", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(w=135, h=8, text="IVA (22%):", align="R")
    pdf.cell(w=40, h=8, text="3.696,00 EUR", align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(w=135, h=10, text="TOTALE:", align="R")
    pdf.cell(w=40, h=10, text="20.496,00 EUR", align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(8)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(
        text="Note: Pagamento tramite bonifico bancario. IBAN: IT60X0542811101000000123456",
        new_x="LMARGIN",
        new_y="NEXT",
    )

    out_path = FIXTURES_DIR / "fattura_test.pdf"
    pdf.output(str(out_path))
    return out_path


def generate_contract_pdf() -> Path:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(text="CONTRATTO QUADRO DI SERVIZI", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("Helvetica", "", 11)
    pdf.cell(text="Numero contratto: MSA-2023-ACME-001", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(text="Data decorrenza: 2024-01-01", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(text="Data scadenza: 2025-12-31", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(text="TRA", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(
        w=0,
        h=6,
        text=(
            "TechConsult S.r.l. (di seguito 'Fornitore'), con sede in Via Roma 42, 20121 Milano, "
            "P.IVA IT12345678901"
        ),
    )
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(text="E", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(
        w=0,
        h=6,
        text=(
            "ACME Italia S.p.A. (di seguito 'Cliente'), con sede in Corso Vittorio Emanuele 100, "
            "00186 Roma, P.IVA IT98765432109"
        ),
    )
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(text="Art. 1 - Oggetto del contratto", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(
        w=0,
        h=6,
        text=(
            "Il Fornitore si impegna a fornire al Cliente servizi di consulenza informatica, "
            "sviluppo software, project management e formazione, secondo le tariffe e le "
            "condizioni stabilite nel presente contratto."
        ),
    )
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(text="Art. 2 - Tariffe e corrispettivi", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(w=0, h=6, text="Le tariffe massime concordate per i servizi sono le seguenti:")
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(w=60, h=8, text="Tipo di servizio", border=1)
    pdf.cell(w=45, h=8, text="Prezzo max", border=1, align="R")
    pdf.cell(w=40, h=8, text="Unita", border=1, align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 10)
    for service, price in [
        ("Consulenza Senior", "500,00 EUR"),
        ("Sviluppo Software", "450,00 EUR"),
        ("Project Management", "550,00 EUR"),
    ]:
        pdf.cell(w=60, h=8, text=service, border=1)
        pdf.cell(w=45, h=8, text=price, border=1, align="R")
        pdf.cell(w=40, h=8, text="giorno/uomo", border=1, align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(2)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(
        w=0,
        h=6,
        text=(
            "Le tariffe sopra indicate sono da intendersi come importi massimi al netto di IVA. "
            "Il Fornitore non potra applicare tariffe superiori senza previo accordo scritto."
        ),
    )
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(text="Art. 3 - Adeguamento prezzi", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(
        w=0,
        h=6,
        text=(
            "Le tariffe potranno essere adeguate annualmente in misura pari alla variazione "
            "dell'indice ISTAT dei prezzi al consumo, previa comunicazione scritta con almeno "
            "90 giorni di anticipo."
        ),
    )
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(text="Art. 4 - Termini di pagamento", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(
        w=0,
        h=6,
        text=(
            "Il pagamento dovra avvenire entro 60 (sessanta) giorni dalla data "
            "di ricevimento della fattura. In caso di ritardo, penale del 2% per ogni mese."
        ),
    )
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(text="Art. 5 - Legge applicabile e foro competente", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(
        w=0,
        h=6,
        text=(
            "Il presente contratto e regolato dalla legge italiana. "
            "Foro competente: Milano."
        ),
    )
    pdf.ln(8)

    pdf.set_font("Helvetica", "", 11)
    pdf.cell(w=90, h=8, text="Per il Fornitore:")
    pdf.cell(w=90, h=8, text="Per il Cliente:", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(w=90, h=8, text="TechConsult S.r.l.")
    pdf.cell(w=90, h=8, text="ACME Italia S.p.A.", new_x="LMARGIN", new_y="NEXT")

    out_path = FIXTURES_DIR / "contratto_test.pdf"
    pdf.output(str(out_path))
    return out_path


def main():
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    invoice_path = generate_invoice_pdf()
    contract_path = generate_contract_pdf()
    print(f"Fattura: {invoice_path} ({invoice_path.stat().st_size:,} bytes)")
    print(f"Contratto: {contract_path} ({contract_path.stat().st_size:,} bytes)")
    print("Discrepanze attese: unit_price, line_total, subtotal, payment_terms")


if __name__ == "__main__":
    main()
