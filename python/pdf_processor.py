"""
PDF Processor Module
Extracts text content from PDF files for exercise generation
"""

import PyPDF2
from io import BytesIO


def extract_text_from_pdf_bytes(pdf_bytes):
    """
    Extract text content from PDF binary data
    
    Args:
        pdf_bytes (bytes): PDF file content as bytes
        
    Returns:
        str: Extracted text from all pages, or None if extraction fails
    """
    try:
        # Create a BytesIO object from bytes
        pdf_file = BytesIO(pdf_bytes)
        
        # Create PDF reader
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        # Extract text from all pages
        text_content = []
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text = page.extract_text()
            if text:
                text_content.append(text)
        
        # Join all pages with newlines
        full_text = '\n\n'.join(text_content)
        
        if not full_text.strip():
            print("Warning: PDF appears to be empty or contains only images")
            return None
            
        return full_text
        
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        import traceback
        traceback.print_exc()
        return None


def extract_text_from_pdf_file(pdf_path):
    """
    Extract text content from PDF file path
    
    Args:
        pdf_path (str): Path to PDF file
        
    Returns:
        str: Extracted text from all pages, or None if extraction fails
    """
    try:
        with open(pdf_path, 'rb') as file:
            pdf_bytes = file.read()
        return extract_text_from_pdf_bytes(pdf_bytes)
    except Exception as e:
        print(f"Error reading PDF file: {e}")
        return None
