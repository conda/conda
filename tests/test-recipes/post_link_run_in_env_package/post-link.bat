
echo "TEST_VAR is set to :%TEST_VAR%:" >> %PREFIX%\.messages.txt
if "%TEST_VAR%"=="1" (
    echo "Success: TEST_VAR is set correctly" >> %PREFIX%\.messages.txt
    exit 0
)
echo "ERROR: TEST_VAR is not set or set incorrectly" >> %PREFIX%\.messages.txt
exit 1
