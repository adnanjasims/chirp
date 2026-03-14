# lightweight Python image to keep container size small
FROM python:3.11-slim

# set the working directory inside the container
WORKDIR /app

# copy requirements file first to leverage Docker cache
COPY requirements.txt .

# install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# copy rest of the backend source code into the container
COPY . .

# expose port 8000 for the Flask API
EXPOSE 8000

# run the Flask application on port 8000
# Binding to 0.0.0.0 is required for Docker to route traffic correctly
CMD ["flask", "--app", "main", "run", "--host=0.0.0.0", "--port=8000"]