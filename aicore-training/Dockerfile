FROM python:3.11-slim
WORKDIR /app
RUN pip install scikit-learn pandas
COPY train.py .
RUN mkdir -p /app/data /app/model
COPY ml_training_data.csv /app/data/ml_training_data.csv
CMD ["python", "train.py"]
