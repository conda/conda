@echo ON

if /I "%PKG_NAME%" == "libmamba-spdlog" (

    cmake -B build-lib-spdlog/ ^
        -G Ninja ^
        %CMAKE_ARGS% ^
        -D BUILD_LIBMAMBA_SPDLOG=ON ^
        -D BUILD_SHARED=ON
    if errorlevel 1 exit 1
    cmake --build build-lib-spdlog/ --parallel %CPU_COUNT%
    if errorlevel 1 exit 1
    cmake --install build-lib-spdlog/

)
if /I "%PKG_NAME%" == "libmamba" (

    cmake -B build-lib/ ^
        -G Ninja ^
        %CMAKE_ARGS% ^
        -D BUILD_SHARED=ON ^
        -D BUILD_LIBMAMBA=ON ^
        -D BUILD_MAMBA_PACKAGE=ON ^
        -D BUILD_LIBMAMBAPY=OFF ^
        -D BUILD_MAMBA=OFF ^
        -D BUILD_MICROMAMBA=OFF
    if errorlevel 1 exit 1
    cmake --build build-lib/ --parallel %CPU_COUNT%
    if errorlevel 1 exit 1
    cmake --install build-lib/

)
if /I "%PKG_NAME%" == "libmambapy" (

    %PYTHON% -m pip install --no-deps --no-build-isolation -vv ./libmambapy

)
if /I "%PKG_NAME%" == "mamba" (

    cmake -B build-mamba/ ^
        -G Ninja ^
        %CMAKE_ARGS% ^
        -D BUILD_LIBMAMBA=OFF ^
        -D BUILD_MAMBA_PACKAGE=OFF ^
        -D BUILD_LIBMAMBAPY=OFF ^
        -D BUILD_MAMBA=ON ^
        -D BUILD_MICROMAMBA=OFF
    if errorlevel 1 exit 1
    cmake --build build-mamba/ --parallel %CPU_COUNT%
    if errorlevel 1 exit 1
    cmake --install build-mamba/
    :: Install BAT hooks in condabin/
    CALL "%LIBRARY_BIN%\mamba.exe" shell hook --shell cmd.exe "%PREFIX%"
    if errorlevel 1 exit 1
)
