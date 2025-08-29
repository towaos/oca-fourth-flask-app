FROM python:3.10
# FROM python:alpine
WORKDIR /var/www
ENV TZ='Asia/Tokyo'
COPY requirements.txt ./
RUN pip install -r requirements.txt
CMD ["uwsgi","--ini","/var/www/uwsgi.ini"]