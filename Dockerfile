FROM python:3.9-slim-buster

WORKDIR /app
ENV PYTHONUNBUFFERED 1
EXPOSE 8000

COPY . .
RUN REQUIREMENTS=$(mktemp) && pip3 install poetry && poetry export -o ${REQUIREMENTS} && pip3 install -r ${REQUIREMENTS}

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]