FROM mongo:latest

COPY . .
COPY crontab /etc/cron.d/crontab
# Give execution rights on the cron job
RUN chmod 0644 /etc/cron.d/crontab

# install Python 3 and cron
RUN apt-get update && apt-get install -y python3 python3-pip cron
RUN pip install -r requirements.txt
RUN crontab /etc/cron.d/crontab

CMD ["cron", "-f"]

EXPOSE 27017