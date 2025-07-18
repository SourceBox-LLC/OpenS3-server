#!/usr/bin/env python3
"""
OpenS3 Setup Script

This script sets up the OpenS3 environment by creating a .env file with user-specified
credentials for authentication. Running this script will prompt for username and password
to be used for HTTP Basic Authentication.
"""

import os
import getpass
import shutil

# Define colors for terminal output
COLORS = {
    'GREEN': '\033[92m',
    'YELLOW': '\033[93m',
    'RED': '\033[91m',
    'BLUE': '\033[94m',
    'ENDC': '\033[0m',
    'BOLD': '\033[1m'
}

def print_color(text, color):
    """Print colored text to terminal"""
    print(f"{COLORS.get(color, '')}{text}{COLORS['ENDC']}")

def create_env_file():
    """Create .env file with user-specified credentials"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env_file_path = os.path.join(script_dir, '.env')
    env_example_path = os.path.join(script_dir, '.env.example')
    
    # Check if .env already exists
    if os.path.exists(env_file_path):
        overwrite = input("\n.env file already exists. Overwrite? (y/n): ").lower() == 'y'
        if not overwrite:
            print_color("Setup cancelled. Existing .env file was not modified.", 'YELLOW')
            return False
    
    # Start with the example template if it exists
    env_content = ""
    if os.path.exists(env_example_path):
        with open(env_example_path, 'r') as example_file:
            env_content = example_file.read()
    else:
        env_content = "# OpenS3 Configuration\n\n"
    
    # Get user input for credentials
    print_color("\nSetup OpenS3 Authentication", 'BOLD')
    print_color("---------------------------", 'BOLD')
    print("\nPlease enter credentials for HTTP Basic Authentication:")
    
    username = input("Username [admin]: ").strip() or "admin"
    password = getpass.getpass("Password [password]: ") or "password"
    
    # Get storage directory
    default_storage = "./storage"
    storage_dir = input(f"\nStorage directory [{default_storage}]: ").strip() or default_storage
    
    # Create the env file content
    env_content = """# OpenS3 Configuration
# Generated by setup.py

# Authentication credentials (OpenAthena compatible)
OPENS3_ACCESS_KEY={username}
OPENS3_SECRET_KEY={password}

# Legacy compatibility variables
USERNAME={username}
PASSWORD={password}

# Storage configuration
BASE_DIR={storage_dir}
""".format(
        username=username,
        password=password,
        storage_dir=storage_dir
    )
    
    # Write the content to .env file
    with open(env_file_path, 'w') as env_file:
        env_file.write(env_content)
    
    print_color("\n✅ .env file created successfully!", 'GREEN')
    print(f"Location: {env_file_path}")
    
    # Ensure the storage directory exists
    storage_path = storage_dir
    if not storage_path.startswith('/'):
        # Convert relative path to absolute
        storage_path = os.path.join(script_dir, storage_path.lstrip('./\\'))
    
    os.makedirs(storage_path, exist_ok=True)
    print_color(f"Storage directory: {storage_path}", 'BLUE')
    
    return True

def install_requirements():
    """Suggest installing requirements"""
    print_color("\nInstallation", 'BOLD')
    print_color("------------", 'BOLD')
    print("\nTo complete the setup, install required packages:")
    print_color("pip install -r requirements.txt", 'BLUE')

def main():
    """Main function"""
    print_color("\nOpenS3 Server Setup", 'BOLD')
    print_color("=================\n", 'BOLD')
    
    # Create .env file
    if create_env_file():
        install_requirements()
        
        print_color("\nSetup Complete!", 'GREEN')
        print("To start the server: python server.py")

if __name__ == "__main__":
    main()
