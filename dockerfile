FROM python:3.10-slim

WORKDIR /app

#COPY requirements.txt .
# Install numpy first with version constraint

COPY . .
RUN chmod +x Runtime.sh
EXPOSE 8501
ENTRYPOINT ["./Runtime.sh"]
