import requests
from io import BytesIO
from PyPDF2 import PdfReader

def extract_text_from_pdf_bytes(pdf_content: bytes) -> str:
    with BytesIO(pdf_content) as f:
        reader = PdfReader(f)
        text = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)
        return "\n".join(text)


def pdf_url_to_text(url: str) -> str:
    """
    Downloads a PDF from the specified URL and returns its text content as a string.
    """
    response = requests.get(url)
    response.raise_for_status()
    return extract_text_from_pdf_bytes(response.content)


async def async_extract_text_from_pdf(pdf_content: bytes) -> str:
    return extract_text_from_pdf_bytes(pdf_content)
