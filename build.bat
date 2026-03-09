@echo off
REM Windows 打包脚本
REM 用法：build.bat
REM 输出：dist\ansys-agent.exe

echo 安装构建依赖...
pip install pyinstaller
if errorlevel 1 goto error

echo 打包中...
pyinstaller ansys-agent.spec --clean
if errorlevel 1 goto error

echo.
echo 完成！可执行文件：dist\ansys-agent.exe
echo 运行：dist\ansys-agent.exe
goto end

:error
echo 打包失败，请检查错误信息。
exit /b 1

:end
