FROM python:3.14-slim

WORKDIR /app

COPY . .

# Dev dependencies are included so the test suite can run inside the container
# (`docker compose run --rm api pytest`).
RUN pip install --no-cache-dir -e ".[dev]"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
