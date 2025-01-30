
chcp 65001

@echo off

set cur_path=%~dp0
echo 当前工作路径：%cur_path%

set input_files_path=%cur_path%data
echo 待转换的文件路径：%input_files_path%

:: 获取当前日期和时间
for /f "tokens=1-4 delims=/ " %%a in ('date /t') do (
    set yy=%%b
    set mm=%%c
    set dd=%%d
)
for /f "tokens=1-3 delims=:." %%a in ('time /t') do (
    set hh=%%a
    set nn=%%b
    set ss=%%c
)
 
:: 处理两位数的月份和日期（如果需要）
@REM if %mm% LSS 10 set mm=0%mm%
@REM if %dd% LSS 10 set dd=0%dd%
@REM if %hh% LSS 10 set hh=0%hh%
@REM if %nn% LSS 10 set nn=0%nn%
 
:: 拼接时间戳
set timestamp=%yy%%mm%%dd%%hh%%nn%%ss%_%RANDOM%
echo %timestamp%

@REM %cur_path%只保留左边的双引号，支持路径为中文且带空格
@REM .\bin\xxx.exe 0 "%input_files_path%" "%cur_path%

set src_file=%input_files_path%\2024条件选股x.xlsx
set dst_file=%input_files_path%\2024条件选股x1.xlsx
set tmp_file=%input_files_path%\2024条件选股x_%timestamp%.xlsx
set sheet_name=条件选股2021
echo src_file= %src_file%
echo dst_file= %dst_file%
echo sheet_name= %sheet_name%
C:/Users/Administrator/AppData/Local/Programs/Python/Python313/python.exe %cur_path%app.py "%src_file%" "%dst_file%" "%sheet_name%" 0
@REM .\app\app.exe 0 "%src_file%" "%dst_file%" "%sheet_name%

move %src_file% %tmp_file%
move %dst_file% %src_file%

pause
