# Whisk Image Generator

This is a Django-based web application that uses the Whisk API to generate images from text prompts.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd whisk-api
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv virtual-env
    source virtual-env/bin/activate
    ```

3.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up the PostgreSQL database:**
    *   Log in to your PostgreSQL server:
        ```bash
        sudo -u postgres psql
        ```
    *   Run the following commands to create the database and user:
        ```sql
        CREATE DATABASE whisk;
        CREATE USER whisk_user WITH PASSWORD 'whisk_password';
        GRANT ALL PRIVILEGES ON DATABASE whisk TO whisk_user;
        ALTER ROLE whisk_user SET client_encoding TO 'utf8';
        ALTER ROLE whisk_user SET default_transaction_isolation TO 'read committed';
        ALTER ROLE whisk_user SET timezone TO 'UTC';
        \q
        ```

5.  **Create a `.env` file** in the root of the project and add the following, replacing the placeholders with your actual credentials:
    ```
    SECRET_KEY='your-secret-key'
    WHISK_COOKIE='your-whisk-cookie'
    DB_NAME='whisk'
    DB_USER='whisk_user'
    DB_PASSWORD='whisk_password'
    DB_HOST='localhost'
    DB_PORT='5432'
    ```

6.  **Run the database migrations:**
    ```bash
    python manage.py migrate
    ```

## Running the Application

1.  **Start the development server:**
    ```bash
    python manage.py runserver
    ```

2.  Open your web browser and navigate to `http://127.0.0.1:8000/` to use the application.