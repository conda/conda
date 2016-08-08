export BACKUP_PATH="$PATH"

# http://unix.stackexchange.com/questions/40749/remove-duplicate-path-entries-with-awk-command
# TO-DO: consider adding more path cleanup like symlinking paths that are longer than __
if [ -n "$PATH" ]; then
  old_PATH="$PATH:"
  PATH=""
  while [ -n "$old_PATH" ]; do
    x=${old_PATH%%:*}       # the first remaining entry
    case $PATH: in
      *:"$x":*) ;;          # already there
      *) PATH=$PATH:$x;;    # not there yet
    esac
    old_PATH=${old_PATH#*:}
  done
  PATH=${PATH#:}
  unset old_PATH x
fi

export PATH="$PATH"
