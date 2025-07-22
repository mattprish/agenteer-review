import requests
from io import BytesIO
from PyPDF2 import PdfReader


def pdf_url_to_text(url: str) -> str:
    response = requests.get(url)
    response.raise_for_status()
    with BytesIO(response.content) as f:
        reader = PdfReader(f)
        text = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)
        return "\n".join(text)
