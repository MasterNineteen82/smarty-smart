import os
import subprocess
import datetime
import logging

# Configuration
REPO_DIR = r'X:\smarty-smart'
LOG_FILE = os.path.join(REPO_DIR, 'gitupdate.log')
BRANCH = 'main'
COMMIT_MESSAGE_PREFIX = "Auto-update"

# Logging setup
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', encoding='utf-8')

def log_message(message, level=logging.INFO):
    logging.log(level, message)

def run_git_command(command):
    try:
        log_message(f"Running: {command}", logging.DEBUG)
        process = subprocess.run(command, shell=True, cwd=REPO_DIR, text=True, capture_output=True)

        if process.returncode == 0:
            if process.stdout:
                log_message(f"✅ {command}\n{process.stdout}", logging.INFO)
            if process.stderr:
                log_message(f"⚠️ Minor issue (stderr): {command}\n{process.stderr}", logging.WARNING)
        else:
            log_message(f"❌ ERROR: {command} failed with return code {process.returncode}\nStderr: {process.stderr}\nStdout: {process.stdout}", logging.ERROR)
            return False  # Indicate failure

        return True  # Indicate success

    except FileNotFoundError as e:
        log_message(f"❌ FileNotFoundError running {command}: {str(e)}. Ensure Git is installed and in your system's PATH.", logging.CRITICAL)
        return False
    except subprocess.CalledProcessError as e:
        log_message(f"❌ CalledProcessError running {command}: {str(e)}. Stderr: {e.stderr}, Stdout: {e.stdout}", logging.ERROR)
        return False
    except Exception as e:
        log_message(f"❌ Exception running {command}: {str(e)}", logging.ERROR)
        return False

def update_git_repo():
    log_message("\n🔄 Starting Git Auto-Update...", logging.INFO)
    try:
        # Check if there are any changes to commit
        status_result = subprocess.run("git status --porcelain", shell=True, cwd=REPO_DIR, text=True, capture_output=True)
        if status_result.stdout.strip():
            run_git_command("git add .")
            commit_message = f"{COMMIT_MESSAGE_PREFIX}: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            if not run_git_command(f'git commit -m "{commit_message}"'):
                log_message("❌ Commit failed, halting update.", logging.WARNING)
                return  # Stop if commit fails
        else:
            log_message("⚠️ No changes to commit.", logging.INFO)

        if not run_git_command(f"git pull origin {BRANCH}"):
            log_message("❌ Pull failed, halting update.", logging.WARNING)
            return

        if not run_git_command(f"git push origin {BRANCH}"):
            log_message("❌ Push failed, halting update.", logging.WARNING)
            return

        log_message("🚀 Git update completed successfully!\n", logging.INFO)

    except Exception as e:
        log_message(f"❌ Error during git update: {e}", logging.ERROR)

def update_project():
    """Updates the project using Git."""

    try:
        # Define paths
        log_file_path = "gitupdate.log"

        # Log the start of the update
        with open(log_file_path, "a") as log_file:
            log_file.write(f"Update started at: {datetime.datetime.now()}\n")

        # Run git pull
        subprocess.run(["git", "pull"], check=True, capture_output=True, text=True)

        # Log the successful update
        with open(log_file_path, "a") as log_file:
            log_file.write(f"Update completed successfully at: {datetime.datetime.now()}\n")

        print("Project updated successfully.")

    except subprocess.CalledProcessError as e:
        print(f"Error updating project: {e}")
        with open(log_file_path, "a") as log_file:
            log_file.write(f"Error updating project: {e}\n")

if __name__ == "__main__":
    update_git_repo()
    update_project()
