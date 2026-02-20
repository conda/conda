import os
from pathlib import Path
from conda.core.initialize import _powershell_profile_content
from conda.common.path import BIN_DIRECTORY

# Automatically get the user's home directory and build the conda prefix path
conda_prefix = str(Path.home() / "anaconda3")

# Generate the PowerShell profile initialization code
hook = _powershell_profile_content(conda_prefix)

# Output file (you might want to vary this depending on OS/shell)
output_path = "test_profile.ps1"

# Write the generated hook to the output file
with open(output_path, "w") as f:
    f.write(hook)

print(f"Wrote to: {output_path}")
