FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt pyproject.toml ./
COPY pdf_to_dxf ./pdf_to_dxf

RUN python -m pip install --no-cache-dir -r requirements.txt

EXPOSE 8765

CMD ["python", "-m", "pdf_to_dxf", "serve", "--host", "0.0.0.0", "--port", "8765"]
