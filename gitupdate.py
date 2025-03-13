import os
import subprocess
import datetime

# Define your repository directory
REPO_DIR = r"X:\Path\To\Your\Repo"  # Change this to your Git directory
BRANCH = "main"  # Change if using a different branch

def run_git_command(command):
    """Runs a Git command in the repository directory and prints the output."""
    process = subprocess.run(command, shell=True, cwd=REPO_DIR, text=True, capture_output=True)
    print(process.stdout)
    if process.stderr:
        print("Error:", process.stderr)

def update_git_repo():
    """Executes the Git workflow: status, add, commit, pull, and push."""
    print("\n🔄 Updating Git repository...\n")

    # Step 1: Check Git Status
    print("📌 Checking Git status...")
    run_git_command("git status")

    # Step 2: Add Changes
    print("\n✅ Adding all changes...")
    run_git_command("git add .")

    # Step 3: Commit Changes with Timestamp
    commit_message = f"Auto-update: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    print(f"\n📝 Committing changes with message: '{commit_message}'...")
    run_git_command(f'git commit -m "{commit_message}"')

    # Step 4: Pull Latest Changes to Avoid Conflicts
    print("\n⬇️ Pulling latest changes from remote...")
    run_git_command(f"git pull origin {BRANCH}")

    # Step 5: Push Changes to GitHub
    print("\n⬆️ Pushing changes to GitHub...")
    run_git_command(f"git push origin {BRANCH}")

    print("\n🚀 Git update completed successfully!")

if __name__ == "__main__":
    update_git_repo()
