FROM python:3.9-slim-buster
    
RUN pip install Flask==2.0.1 requests==2.26.0 azure-storage-blob==12.8.1 flask-cors

COPY flask_app.py flask_app.py

EXPOSE 5000

CMD ["python", "flask_app.py"]