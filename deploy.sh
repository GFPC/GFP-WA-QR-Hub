#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Project directory (assuming script is in the project root)
PROJECT_DIR="$(dirname "$(realpath "$0")")"
VENV_DIR="$PROJECT_DIR/venv"
REQUIREMENTS_FILE="$PROJECT_DIR/requirements.txt"
MAIN_APP_FILE="$PROJECT_DIR/main.py"
INIT_DB_SCRIPT="$PROJECT_DIR/scripts/init_db.py"

echo "Starting deployment script for GFP Watcher-QR..."
echo "Project directory: $PROJECT_DIR"

# 1. Create a virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment at $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
    echo "Virtual environment created."
fi

# 2. Activate the virtual environment BEFORE changing directory
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"
echo "Virtual environment activated."

# 3. CD into project directory for running Python modules/commands
# This is crucial for correct module imports like 'db'
pushd "$PROJECT_DIR"

# 4. Install dependencies
echo "Installing/Upgrading Python dependencies from $REQUIREMENTS_FILE..."
pip install --no-input --upgrade pip setuptools wheel
pip install --no-input -r "$REQUIREMENTS_FILE"
echo "Dependencies installed."

# 5. Run Alembic migrations (assuming Alembic is set up)
# Note: You might need to configure Alembic correctly beforehand.
if [ -d "alembic" ]; then # No $PROJECT_DIR here since we are already inside it
    echo "Running Alembic migrations..."
    # alembic must be run from the project root where alembic.ini is
    "$VENV_DIR/bin/alembic" upgrade head # Explicitly use venv's alembic
    echo "Alembic migrations completed."
else
    echo "Alembic directory not found, skipping migrations. Please set up Alembic if needed."
fi

# 6. Initialize database (create tables and default admin user)
# Run init_db.py as a module to ensure correct package imports
if [ -f "scripts/init_db.py" ]; then
    echo "Initializing database and ensuring admin user exists..."
    "$VENV_DIR/bin/python" -m scripts.init_db # Explicitly use venv's python and run as module
    echo "Database initialization completed."
else
    echo "Database initialization script not found, skipping. Please ensure your database is set up."
fi

# Pop back to original directory
popd

# 7. Deactivate the virtual environment
deactivate
echo "Virtual environment deactivated."

echo "Deployment script finished successfully!"
echo "Next steps: Configure systemd service." 