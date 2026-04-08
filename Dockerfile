FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY src /app/src
COPY policies /app/policies
COPY schemas /app/schemas
COPY spec /app/spec
COPY examples /app/examples

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["workledger-server"]

