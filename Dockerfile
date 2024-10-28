FROM python:3.11.6

# Install dependencies required by OpenCV
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0

WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
COPY . .
EXPOSE 5000
CMD [ "python", "app.py" ]

## Build the image
## docker build -t flask-app .
## Run the container
## docker run -p 5001:5000 flask-app