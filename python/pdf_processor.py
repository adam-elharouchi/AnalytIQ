"""
PDF Processing Service
Extracts text from PDF files for chapter content
"""
import PyPDF2
import io
import os

def extract_text_from_pdf(pdf_path):
    """
    Extract text from a PDF file
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        str: Extracted text from the PDF
    """
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            
            # Extract text from all pages
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n\n"
            
            return text.strip()
    except Exception as e:
        raise Exception(f"Error extracting text from PDF: {str(e)}")

def extract_text_from_pdf_bytes(pdf_bytes):
    """
    Extract text from PDF bytes (in-memory)
    
    Args:
        pdf_bytes: PDF file content as bytes
        
    Returns:
        str: Extracted text from the PDF
    """
    try:
        pdf_stream = io.BytesIO(pdf_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_stream)
        text = ""
        
        # Extract text from all pages
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text += page.extract_text() + "\n\n"
        
        return text.strip()
    except Exception as e:
        raise Exception(f"Error extracting text from PDF bytes: {str(e)}")

def get_pdf_metadata(pdf_path):
    """
    Get metadata from PDF file
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        dict: PDF metadata (title, author, number of pages, etc.)
    """
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            metadata = pdf_reader.metadata or {}
            
            return {
                'title': metadata.get('/Title', ''),
                'author': metadata.get('/Author', ''),
                'num_pages': len(pdf_reader.pages),
                'subject': metadata.get('/Subject', '')
            }
    except Exception as e:
        return {
            'title': '',
            'author': '',
            'num_pages': 0,
            'subject': ''
        }
