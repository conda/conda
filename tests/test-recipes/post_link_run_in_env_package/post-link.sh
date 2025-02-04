# send feedback to .messages to make debugging easier
echo "TEST_VAR is set to :${TEST_VAR}:" >> "$PREFIX/.messages.txt"
if [ "${TEST_VAR}" != "1" ]; then
    echo "Error: TEST_VAR is not set or set incorrectly" >> "$PREFIX/.messages.txt";
    exit 1;
fi
echo "Success: TEST_VAR is set correctly" >> "$PREFIX/.messages.txt"
exit 0
