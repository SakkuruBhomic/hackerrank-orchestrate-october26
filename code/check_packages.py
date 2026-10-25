import os
import pypdf # or let's check if pypdf or pdfplumber is installed

try:
    import pypdf
    print("pypdf installed")
except ImportError:
    try:
        import PyPDF2
        print("PyPDF2 installed")
    except ImportError:
        print("no pypdf")

# Check if PIL/pytesseract is installed
try:
    from PIL import Image
    print("PIL installed")
except ImportError:
    print("no PIL")
