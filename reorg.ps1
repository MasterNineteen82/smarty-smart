# This script reorganizes the project files into a standardized folder structure.

# Define the root directory
$rootPath = Get-Location

# Define directories to create
$directories = @(
    "app", "app\api", "app\core", "app\db", "app\nfc",
    "tests", "tests\test_api", "tests\test_core", "tests\test_nfc",
    "static", "templates", "logs", "data", "backups", "documents"
)

# Create directories, handling potential errors
foreach ($dir in $directories) {
    $fullPath = Join-Path $rootPath $dir
    try {
        if (!(Test-Path -Path $fullPath)) {
            Write-Host "Creating directory: $fullPath"
            New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
        } else {
            Write-Host "Directory already exists: $fullPath"
        }
    }
    catch {
        Write-Error "Failed to create directory '$fullPath': $($_.Exception.Message)"
    }
}

# Define file movements
# The script now assumes that the files are already in their destination directories
# and only moves the directories that were not moved correctly in the previous run.
$fileMovements = @(
    # The following line has been removed to prevent the error
    # @{ Source = "backups"; Destination = "logs\" },
    # @{ Source = "data"; Destination = "." },
    # @{ Source = "documents"; Destination = "." },
    # @{ Source = "logs"; Destination = "." },
    # @{ Source = "static"; Destination = "." },
    # @{ Source = "templates"; Destination = "." },
    # @{ Source = "tests"; Destination = "." }
)

# Move files, handling potential errors and missing files
foreach ($move in $fileMovements) {
    $sourcePath = Join-Path $rootPath $move.Source
    $destPath = Join-Path $rootPath $move.Destination
    try {
        if (Test-Path -Path $sourcePath) {
            Write-Host "Moving '$sourcePath' to '$destPath'"
            Move-Item -Path $sourcePath -Destination $destPath -Force
        } else {
            Write-Warning "Source file not found: $sourcePath"
        }
    }
    catch {
        Write-Error "Failed to move '$sourcePath' to '$destPath': $($_.Exception.Message)"
    }
}

Write-Host "Folder structure reorganization completed."