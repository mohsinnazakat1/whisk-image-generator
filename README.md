# Whisk Image Generator

A Django-based web application that leverages the Whisk API to generate images from text prompts. Features include:

- Single image generation with instant preview and download options
- Bulk image generation for multiple prompts
- Real-time status tracking for bulk generations
- Clean and intuitive user interface

## Features

### Single Image Generation

- Direct image generation without database storage
- Instant preview functionality
- One-click download option
- Real-time error feedback

### Bulk Image Generation

- Process multiple prompts simultaneously
- Background task processing with Celery
- Progress tracking for each image
- Status dashboard for bulk requests

1. **Clone the repository:**

    ```bash
    git clone <repository-url>
    cd whisk-api
    ```

2. **Install Redis:**
    - **On macOS (using Homebrew):**

        ```bash
        brew install redis
        ```

    - **On Ubuntu/Debian:**

        ```bash
        sudo apt-get update
        sudo apt-get install redis-server
        ```

3. **Create and activate a virtual environment:**

    ```bash
    python3 -m venv virtual-env
    source virtual-env/bin/activate
    ```

4. **Install the dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

5. **Set up the PostgreSQL database:**
    - Log in to your PostgreSQL server:

        ```bash
        sudo -u postgres psql
        ```

    - Run the following commands to create the database and user:

        ```sql
        CREATE DATABASE image_gen_db;
        CREATE USER image_gen_user WITH PASSWORD 'image_gen_password';
        GRANT ALL PRIVILEGES ON DATABASE image_gen_db TO image_gen_user;
        ALTER ROLE image_gen_user SET client_encoding TO 'utf8';
        ALTER ROLE image_gen_user SET default_transaction_isolation TO 'read committed';
        ALTER ROLE image_gen_user SET timezone TO 'UTC';
        \q
        ```

6. **Create a `.env` file** in the root of the project and add the following, replacing the placeholders with your actual credentials:

    ```
    SECRET_KEY='your-secret-key'
    WHISK_COOKIE='your-whisk-cookie'
    DB_NAME='whisk'
    DB_USER='whisk_user'
    DB_PASSWORD='whisk_password'
    DB_HOST='localhost'
    DB_PORT='5432'
    ```

7. **Run the database migrations:**

    ```bash
    python manage.py migrate
    ```

## Running the Application

1. **Start Redis:**

    ```bash
    redis-server
    ```

2. **Start the Celery worker:**
    - Open a new terminal window, navigate to the project directory, and activate the virtual environment.
    - Run the following command:

        ```bash
        celery -A whisk_project worker -l info
        ```

3. **Start the development server:**
    - Open another new terminal window, navigate to the project directory, and activate the virtual environment.
    - Run the following command:

        ```bash
        python manage.py runserver
        ```

4. Open your web browser and navigate to `http://127.0.0.1:8000/` to use the application.
