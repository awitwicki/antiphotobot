FROM python:3.11-slim
WORKDIR /app

# Install other dependencies
COPY requirements.txt .
RUN pip3 install -r requirements.txt

COPY src/ .
ENTRYPOINT ["python"]
CMD ["main.py"]
