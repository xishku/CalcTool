
chcp 65001

@echo off

set cur_path=%~dp0
echo 当前工作路径：%cur_path%

set input_files_path=%cur_path%data
echo 待转换的文件路径：%input_files_path%

@REM %cur_path%只保留左边的双引号，支持路径为中文且带空格
@REM .\bin\xxx.exe 0 "%input_files_path%" "%cur_path%

set src_file=%input_files_path%\2024条件选股x.xlsx
set dst_file=%input_files_path%\2024条件选股x.xlsx
set sheet_name=条件选股2021
echo src_file= %src_file%
echo dst_file= %dst_file%
echo sheet_name= %sheet_name%
C:/Users/Administrator/AppData/Local/Programs/Python/Python313/python.exe e:/dev/stock1229-20250105/app/app.py "%src_file%" "%dst_file%" "%sheet_name%"
@REM .\app\app.exe 0 "%src_file%" "%dst_file%" "%sheet_name%

pause
