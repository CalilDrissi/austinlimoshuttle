# Backend image — Django API + staff dashboard.
#
# Python 3.12 matches the InMotion production runtime (verified 3.12.13).
# Every dependency installs from a pure-Python wheel (PyMySQL, xhtml2pdf, …),
# so no C toolchain is needed — the same constraint the shared host imposes.

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencies first, for layer caching.
COPY requirements/ requirements/
RUN pip install -r requirements/dev.txt

COPY . .

ENTRYPOINT ["bash", "/app/docker-entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
