FROM python:3.11-slim
WORKDIR /app
RUN pip install scikit-learn pandas
COPY train.py .
CMD ["python", "train.py"]
