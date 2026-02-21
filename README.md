# AI Document Companion

Small project to process and analyze documents using `unstructured` and FastAPI.

Getting started

1. Install system dependencies on macOS:

   brew install libmagic poppler tesseract

2. Create a Python virtual environment and install Python packages:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the app (example):

```bash
uvicorn main:app --reload
```

License

This project is available under the MIT License — see `LICENSE`.
