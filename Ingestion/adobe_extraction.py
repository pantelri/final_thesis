import logging
import json 
from pathlib import Path


from adobe.pdfservices.operation.auth.service_principal_credentials import (ServicePrincipalCredentials,)
from adobe.pdfservices.operation.io.cloud_asset import CloudAsset
from adobe.pdfservices.operation.io.stream_asset import StreamAsset
from adobe.pdfservices.operation.pdf_services import PDFServices
from adobe.pdfservices.operation.pdf_services_media_type import PDFServicesMediaType
from adobe.pdfservices.operation.pdfjobs.jobs.extract_pdf_job import ExtractPDFJob
from adobe.pdfservices.operation.pdfjobs.params.extract_pdf.extract_element_type import (ExtractElementType)
from adobe.pdfservices.operation.pdfjobs.params.extract_pdf.extract_pdf_params import (ExtractPDFParams)
from adobe.pdfservices.operation.pdfjobs.params.extract_pdf.table_structure_type import (TableStructureType)
from adobe.pdfservices.operation.pdfjobs.result.extract_pdf_result import (ExtractPDFResult)

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


def extract_pdf_with_adobe(
    pdf_path: Path,
    credentials: ServicePrincipalCredentials,
) -> bytes:
    """
    Lädt die PDF zur Adobe PDF Services API hoch und gibt den
    Inhalt des Ergebnis-ZIPs als Bytes zurück.

    Extrahiert:
      - Strukturierten Text (Text + Überschriften + Listen)
      - Tabellen (als Strukturelemente + CSV-Rendition)
    """
    logger.info("Starte Adobe-Extraktion für: %s", pdf_path.name)

    with open(pdf_path, "rb") as fh:
        input_stream = fh.read()

    pdf_services = PDFServices(credentials=credentials)
    input_asset  = pdf_services.upload(
        input_stream=input_stream,
        mime_type=PDFServicesMediaType.PDF,
    )

    extract_params = ExtractPDFParams(
        elements_to_extract=[ExtractElementType.TEXT, ExtractElementType.TABLES],
        table_structure_type=TableStructureType.CSV,   # CSV-Rendition für Tabellen
    )

    job      = ExtractPDFJob(input_asset=input_asset, extract_pdf_params=extract_params)
    location = pdf_services.submit(job)
    response = pdf_services.get_job_result(location, ExtractPDFResult)

    result_asset: CloudAsset  = response.get_result().get_resource()
    stream_asset: StreamAsset = pdf_services.get_content(result_asset)

    logger.info("Adobe-Extraktion abgeschlossen.")
    return stream_asset.get_input_stream()

def load_credentials(credentials_path: Path) -> ServicePrincipalCredentials:
    """Liest Client-ID und Client-Secret aus der JSON-Credentials-Datei."""
    with open(credentials_path, "r", encoding="utf-8") as fh:
        creds = json.load(fh)
    client_id     = creds["client_credentials"]["client_id"]
    client_secret = creds["client_credentials"]["client_secret"]
    logger.info("Credentials geladen (client_id=%s…)", client_id[:8])
    return ServicePrincipalCredentials(
        client_id=client_id,
        client_secret=client_secret,
    )