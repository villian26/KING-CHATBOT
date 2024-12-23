FROM python:latest

# Update and install necessary system packages
RUN apt-get update -y && apt-get upgrade -y
RUN apt-get install -y build-essential libssl-dev libffi-dev python3-dev

# Upgrade pip, setuptools, and wheel
RUN pip3 install --upgrade pip setuptools wheel

# Copy the application files and install Python dependencies
COPY . /app/
WORKDIR /app/
RUN pip3 install -U -r requirements.txt

# Command to run the application
CMD bash start
