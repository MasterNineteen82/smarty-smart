import os
import subprocess
import datetime
import win32com.client  # Requires `pywin32`
import logging
import sys

# Configuration
REPO_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT_PATH = os.path.join(REPO_DIR, "gitupdate.py")
BAT_FILE_PATH = os.path.join(REPO_DIR, "gitupdate.bat")
LOG_FILE = os.path.join(REPO_DIR, "gitupdate.log")
TASK_NAME = "AutoGitUpdate"
BRANCH = 'main'  # Default branch, can be overridden
COMMIT_MESSAGE_PREFIX = "Auto-update"
UPDATE_INTERVAL_MINUTES = 30
UPDATE_DURATION_DAYS = 1
TASK_EXECUTION_LIMIT_HOURS = 1

# Logging setup
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', encoding='utf-8')

def log_message(message, level=logging.INFO):
    """Logs messages with a timestamp and level."""
    print(message)  # Print to console as well
    logging.log(level, message)

def create_gitupdate_script():
    """Creates gitupdate.py if it doesn't exist, with robust error handling."""
    if os.path.exists(SCRIPT_PATH):
        log_message(f"gitupdate.py already exists at {SCRIPT_PATH}", logging.INFO)
        return

    log_message("Creating gitupdate.py script...", logging.INFO)
    try:
        script_content = f"""import os
import subprocess
import datetime
import logging

# Configuration
REPO_DIR = r'{REPO_DIR}'
LOG_FILE = os.path.join(REPO_DIR, 'gitupdate.log')
BRANCH = '{BRANCH}'
COMMIT_MESSAGE_PREFIX = "{COMMIT_MESSAGE_PREFIX}"

# Logging setup
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', encoding='utf-8')

def log_message(message, level=logging.INFO):
    logging.log(level, message)

def run_git_command(command):
    try:
        log_message(f"Running: {{command}}", logging.DEBUG)
        process = subprocess.run(command, shell=True, cwd=REPO_DIR, text=True, capture_output=True)

        if process.returncode == 0:
            if process.stdout:
                log_message(f"✅ {{command}}\\n{{process.stdout}}", logging.INFO)
            if process.stderr:
                log_message(f"⚠️ Minor issue (stderr): {{command}}\\n{{process.stderr}}", logging.WARNING)
        else:
            log_message(f"❌ ERROR: {{command}} failed with return code {{process.returncode}}\\nStderr: {{process.stderr}}\\nStdout: {{process.stdout}}", logging.ERROR)
            return False  # Indicate failure

        return True  # Indicate success

    except FileNotFoundError as e:
        log_message(f"❌ FileNotFoundError running {{command}}: {{str(e)}}. Ensure Git is installed and in your system's PATH.", logging.CRITICAL)
        return False
    except subprocess.CalledProcessError as e:
        log_message(f"❌ CalledProcessError running {{command}}: {{str(e)}}. Stderr: {{e.stderr}}, Stdout: {{e.stdout}}", logging.ERROR)
        return False
    except Exception as e:
        log_message(f"❌ Exception running {{command}}: {{str(e)}}", logging.ERROR)
        return False

def update_git_repo():
    log_message("\\n🔄 Starting Git Auto-Update...", logging.INFO)
    try:
        # Check if there are any changes to commit
        status_result = subprocess.run("git status --porcelain", shell=True, cwd=REPO_DIR, text=True, capture_output=True)
        if status_result.stdout.strip():
            run_git_command("git add .")
            commit_message = f"{{COMMIT_MESSAGE_PREFIX}}: {{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}}"
            if not run_git_command(f'git commit -m "{{commit_message}}"'):
                log_message("❌ Commit failed, halting update.", logging.WARNING)
                return  # Stop if commit fails
        else:
            log_message("⚠️ No changes to commit.", logging.INFO)

        if not run_git_command(f"git pull origin {{BRANCH}}"):
            log_message("❌ Pull failed, halting update.", logging.WARNING)
            return

        if not run_git_command(f"git push origin {{BRANCH}}"):
            log_message("❌ Push failed, halting update.", logging.WARNING)
            return

        log_message("🚀 Git update completed successfully!\\n", logging.INFO)

    except Exception as e:
        log_message(f"❌ Error during git update: {{e}}", logging.ERROR)

if __name__ == "__main__":
    update_git_repo()
"""
        with open(SCRIPT_PATH, "w", encoding="utf-8") as script_file:
            script_file.write(script_content)
        log_message("✅ gitupdate.py created.", logging.INFO)
    except Exception as e:
        log_message(f"❌ Error creating gitupdate.py: {e}", logging.ERROR)
        sys.exit(1)  # Exit if script creation fails

def create_bat_file():
    """Creates a .bat file to run the script silently, with error handling."""
    if os.path.exists(BAT_FILE_PATH):
        log_message(f"gitupdate.bat already exists at {BAT_FILE_PATH}", logging.INFO)
        return

    log_message("Creating gitupdate.bat...", logging.INFO)
    try:
        bat_content = f"""@echo off
python "{SCRIPT_PATH}"
exit"""
        with open(BAT_FILE_PATH, "w", encoding="utf-8") as bat_file:
            bat_file.write(bat_content)
        log_message("✅ gitupdate.bat created.", logging.INFO)
    except Exception as e:
        log_message(f"❌ Error creating gitupdate.bat: {e}", logging.ERROR)
        sys.exit(1)  # Exit if bat file creation fails

def schedule_task():
    """Schedules the task in Windows Task Scheduler, with extensive error handling and logging."""
    log_message("Scheduling Task in Task Scheduler...", logging.INFO)

    try:
        scheduler = win32com.client.Dispatch("Schedule.Service")
        scheduler.Connect()
        root_folder = scheduler.GetFolder("\\")

        # Task Deletion (Improved)
        try:
            root_folder.DeleteTask(TASK_NAME, 0)
            log_message("⚠️ Old Task Removed.", logging.WARNING)
        except Exception as e:
            # Task may not exist, which is fine.  Only log if it's a different error.
            if "The specified task name could not be found" not in str(e):
                log_message(f"⚠️ Could not remove old task (if it existed): {e}", logging.WARNING)

        task = scheduler.NewTask(0)

        # Set task parameters
        task.RegistrationInfo.Description = "Automatically updates Git repository"
        task.Principal.LogonType = 3  # Logon type: Interactive
        task.Settings.Enabled = True
        task.Settings.Hidden = False  # Show in Task Scheduler for debugging
        task.Settings.AllowDemandStart = True

        # ✅ **Fix: Set a valid ExecutionTimeLimit**
        task.Settings.ExecutionTimeLimit = f"PT{TASK_EXECUTION_LIMIT_HOURS}H"  # 1-hour limit instead of PT0
        task.Settings.DisallowStartIfOnBatteries = False  # Allow on battery
        task.Settings.StopIfGoingOnBatteries = False  # Don't stop if unplugged
        task.Settings.StartWhenAvailable = True  # Ensure it runs even after missed start

        # Trigger - Repeat every UPDATE_INTERVAL_MINUTES minutes
        trigger = task.Triggers.Create(1)  # 1 = TimeTrigger
        trigger.StartBoundary = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        trigger.Repetition.Interval = f"PT{UPDATE_INTERVAL_MINUTES}M"  # Every 30 minutes
        trigger.Repetition.Duration = f"P{UPDATE_DURATION_DAYS}D"  # Repeat for 1 day
        trigger.Enabled = True  # Ensure trigger is enabled

        # Action - Run .bat file
        action = task.Actions.Create(0)  # 0 = Execute
        action.Path = BAT_FILE_PATH
        action.WorkingDirectory = REPO_DIR  # Set working directory

        # Register Task
        try:
            root_folder.RegisterTaskDefinition(
                TASK_NAME, task, 6, None, None, 3
            )
            log_message(f"✅ Task scheduled to run every {UPDATE_INTERVAL_MINUTES} minutes.", logging.INFO)
        except Exception as register_error:
            log_message(f"❌ Error registering task: {register_error}", logging.ERROR)
            sys.exit(1)

    except Exception as e:
        log_message(f"❌ Error scheduling task: {e}", logging.ERROR)
        sys.exit(1)

def run_gitupdate_now():
    """Runs gitupdate.py immediately, handling potential errors extensively."""
    log_message("\n🚀 Running Git Update for the First Time...", logging.INFO)
    try:
        result = subprocess.run(["python", SCRIPT_PATH], cwd=REPO_DIR, capture_output=True, text=True, check=False)

        if result.returncode == 0:
            log_message("✅ Initial Git update completed.", logging.INFO)
        else:
            log_message(f"❌ Initial Git update failed with return code {result.returncode}.", logging.ERROR)
            if result.stdout:
                log_message(f"Stdout: {result.stdout}", logging.ERROR)
            if result.stderr:
                log_message(f"Stderr: {result.stderr}", logging.ERROR)

    except FileNotFoundError:
        log_message("❌ Python interpreter not found. Ensure Python is installed and in your system's PATH.", logging.CRITICAL)
        sys.exit(1)
    except Exception as e:
        log_message(f"❌ An unexpected error occurred during the initial Git update: {e}", logging.ERROR)
        sys.exit(1)

def setup_git():
    """Sets up the Git environment for the project."""

    try:
        # Check if Git is installed
        subprocess.run(["git", "--version"], check=True, capture_output=True)

        # Initialize Git repository if it doesn't exist
        if not os.path.exists(".git"):
            subprocess.run(["git", "init"], check=True)

        # Set up pre-commit hook (example)
        hook_path = os.path.join(".git", "hooks", "pre-commit")
        with open(hook_path, "w") as f:
            f.write("#!/bin/sh\npython " + SCRIPT_PATH + "\n")
        os.chmod(hook_path, 0o755)

        print("Git environment set up successfully.")

    except FileNotFoundError:
        print("Git is not installed. Please install Git and try again.")
    except subprocess.CalledProcessError as e:
        print(f"Error setting up Git environment: {e}")

if __name__ == "__main__":
    log_message("🔄 Starting Setup for Automated Git Updates...\n", logging.INFO)

    # Check for pywin32
    try:
        win32com.client.Dispatch("Schedule.Service")
    except Exception as e:
        log_message(f"❌ pywin32 is not installed. Please install it with: pip install pywin32.  Task scheduling will not work.  Error: {e}", logging.CRITICAL)
        sys.exit(1)

    # Ensure log file exists
    try:
        if not os.path.exists(LOG_FILE):
            open(LOG_FILE, "w", encoding="utf-8").close()
    except Exception as e:
        log_message(f"❌ Error creating log file: {e}", logging.ERROR)
        sys.exit(1)

    create_gitupdate_script()
    create_bat_file()
    schedule_task()
    run_gitupdate_now()
    setup_git()

    log_message(f"\n✅ Setup Complete! Git will auto-update every {UPDATE_INTERVAL_MINUTES} minutes.", logging.INFO)
    sys.exit(0)
