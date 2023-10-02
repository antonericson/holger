FROM mongo:latest

COPY . .

# install Python 3 and cron
RUN apt-get update && apt-get install -y python3 python3-pip crond
RUN pip install -r requirements.txt
RUN crontab crontab

CMD ["crond", "-f"]

EXPOSE 27017