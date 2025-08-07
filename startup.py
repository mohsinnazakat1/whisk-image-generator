import subprocess
import os
import time
import sys

def is_process_running(process_name):
    """Check if a process with the given name is running."""
    try:
        # Use pgrep to find the process
        subprocess.check_output(["pgrep", "-f", process_name])
        return True
    except subprocess.CalledProcessError:
        return False

def start_celery_worker():
    """Starts the Celery worker in the background."""
    if is_process_running("celery -A image_generator worker"):
        print("Celery worker is already running.")
        return

    print("Starting Celery worker...")
    # Get the absolute path to the celery executable in the virtual env
    venv_path = os.environ.get("VIRTUAL_ENV")
    if not venv_path:
        print("Error: Virtual environment is not activated.")
        sys.exit(1)
        
    celery_executable = os.path.join(venv_path, "bin", "celery")
    command = f"{celery_executable} -A image_generator worker --loglevel=info"
    
    # Using subprocess.Popen to run it in the background
    with open("celery_worker.log", "wb") as log_file:
        subprocess.Popen(command.split(), stdout=log_file, stderr=log_file)
    
    # Give it a moment to start up
    time.sleep(5)
    
    if is_process_running("celery -A image_generator worker"):
        print("Celery worker started successfully.")
    else:
        print("Error: Celery worker failed to start. Check celery_worker.log for details.")
        sys.exit(1)


def start_django_server():
    """Starts the Django development server."""
    print("Starting Django development server at http://127.0.0.1:8000/")
    command = "python manage.py runserver"
    try:
        subprocess.run(command.split())
    except KeyboardInterrupt:
        print("\nDjango development server stopped.")
    except Exception as e:
        print(f"An error occurred while running the Django server: {e}")

if __name__ == "__main__":
    # Important: Make sure you have activated your virtual environment
    # before running this script.
    
    # Start the Celery worker
    start_celery_worker()
    
    # Start the Django server
    start_django_server()
