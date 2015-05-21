# Define a function 'conda' allowing you to use 'conda activate' and 'conda
# deactivate' instead of 'source activate' and 'source deactivate'.

# Usage: Put

# source ~/anaconda/lib/python2.7/site-packages/conda/conda-bash.sh

# in your bash profile (replace the above with the path to your root Anaconda
# installation).

# Save the actual conda command, since we override it. Note, we use "which"
# here to ensure we get the 'real' conda, not the function defined below.
CONDA="$(which conda)"

conda () {
    case "$1" in
        "deactivate")
            shift
            # In bash $func is not the same as $func ""
            if [[ -n "$@" ]]; then
                source deactivate "$@"
            else
                source deactivate
            fi
            ;;
        "activate")
            shift
            if [[ -n "$@" ]]; then
                source activate "$@"
            else
                source activate
            fi
            ;;
        *)
            $CONDA "$@"
            ;;
    esac
}
