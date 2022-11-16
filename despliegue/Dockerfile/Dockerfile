FROM python3.9
WORKDIR code
ENV FLASK_APP main.py
ENV FLASK_RUN_HOST 0.0.0.0
COPY . .
RUN ls
RUN pip install -r requirements.txt
CMD [flask, run]