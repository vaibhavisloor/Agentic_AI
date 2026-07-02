import fitz
from pydantic import BaseModel, ValidationError, field_validator

def extract_text(pdf_path: str) -> str:
    with fitz.open(pdf_path) as doc:
        text = ""
        for page in doc:
            text += page.get_text()

        return text


def add_user_info(name: str, email: str, contact_number: str | int) -> dict:
    with open('contact_info.txt','a') as file:
        file.write(f'{name} | {email} | {contact_number}\n')
