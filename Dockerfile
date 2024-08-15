FROM python:3.9-slim-buster
RUN pip install flask werkzeug flask_sqlalchemy requests 
COPY app /app
WORKDIR /app
EXPOSE 7005
CMD python -u app.py