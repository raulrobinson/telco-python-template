FROM python:3.11
WORKDIR /code
ENV FLASK_APP RadiusSocket.py
ENV FLASK_RUN_HOST 0.0.0.0
COPY . .
RUN ls
CMD ["flask", "run"]