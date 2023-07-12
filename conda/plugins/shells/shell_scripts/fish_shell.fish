#!/usr/bin/fish

# Check if we're in this file
echo "Running fish shell script"

# Join all arguments into a single string
set args (string join " " $argv)

# Evaluate the arguments
eval $args

# Activate a new instance of the current shell
fish
