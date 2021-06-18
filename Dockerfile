FROM python:3.9-slim-buster

WORKDIR /app
ENV PYTHONUNBUFFERED 1

RUN pip3 install poetry

COPY . .
RUN poetry install --no-dev

CMD ["poetry", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]