FROM python:3.10 as python-base

RUN mkdir eduvacity
WORKDIR /eduvacity
COPY /pyproject.toml /eduvacity

RUN pip3 install poetry
RUN poetry config virtualenvs.create false
RUN poetry install 

COPY . .
EXPOSE 8000
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "main:app", "--bind", "0.0.0.0:8000"]