if [[ $(stat ${PREFIX}/bin/file) ]]; then
  return 0
fi

return 1
