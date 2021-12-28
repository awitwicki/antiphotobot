FROM python:3.7-buster
WORKDIR /app

# Install tensorflow lite package tflite_runtime
RUN pip3 install --extra-index-url https://google-coral.github.io/py-repo/ tflite_runtime

# Install other dependencies
COPY ./requirements.txt .
RUN pip3 install -r requirements.txt
COPY . .
ENTRYPOINT ["python"]
CMD ["main.py"]
