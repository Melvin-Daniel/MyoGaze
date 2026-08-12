# NeuroShift Control App
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# Frontend should be built before image build: web/dist
ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uvicorn", "src.neuroshift.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
