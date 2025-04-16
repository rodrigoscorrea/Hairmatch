# Use an official Python runtime as a parent image
FROM python:3.9

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files, including entrypoint.sh
COPY . .

# Ensure entrypoint.sh has execute permissions
RUN chmod +x /app/entrypoint.sh

# Expose the port Django runs on
EXPOSE 8000

# Set the entrypoint
ENTRYPOINT ["/bin/sh", "/app/backend/entrypoint.sh"]