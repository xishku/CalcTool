

set version_no=0.01

xcopy ..\src . /E /Y

pyinstaller app.spec

copy .\runapp*.bat .\dist /Y
copy .\*.md .\dist /Y

del .\CalcTool /q /f /s
rmdir .\CalcTool /q /s

md .\dist\data
xcopy .\data\*.xlsx .\dist\data /E /Y

md .\dist\app
echo Current directory: %cd%
move .\dist\*.exe .\dist\app

del .\CalcTool_%version_no% /q /f /s
rmdir .\CalcTool_%version_no% /q /s
@REM move .\dist .\CalcTool_%version_no%
xcopy .\dist\* .\CalcTool_%version_no%\ /E /Y

tar -zcvf CalcTool_%version_no%.tar.gz .\CalcTool_%version_no%

del .\output /q /f /s
rmdir .\output /q /s
md .\output\CalcTool_%version_no%
move .\CalcTool_%version_no% .\output\CalcTool_%version_no%
move .\CalcTool_%version_no%.tar.gz output

del .\build /q /f /s
rmdir .\build /q /s

pause

