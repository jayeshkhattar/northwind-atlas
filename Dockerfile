FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN useradd --create-home appuser \
    && mkdir -p /app/data/conversations /app/data/uploads /app/data/kb \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8501

CMD ["streamlit", "run", "src/ui.py", "--server.address=0.0.0.0"]