;%%%%%%%%%%  copier  %%%%%%%%%%


@echo off
setlocal enabledelayedexpansion

rem 切換到 UTF-8 編碼
chcp 65001
echo.

rem 檢查 copypath.ini 是否存在，若不存在則生成
if not exist "copypath.ini" (
    echo copypath.ini 不存在，正在創建...
    (
    echo ;請輸入來源與輸出資料夾路徑，不要含空格
    echo.
    echo [Path1]
    echo from_folder_path=來源資料夾路徑
    echo [Path2]
    echo to_folder_path=輸出資料夾路徑
    ) > copypath.ini
    echo copypath.ini 已生成，請開啟並設置資料夾路徑。
    echo.
    pause
    exit /b
)

rem 讀取 ini 檔案
for /f "tokens=1,2 delims==" %%A in ('findstr "=" copypath.ini') do (
    if "%%A"=="from_folder_path" set "source_folder=%%B"
    if "%%A"=="to_folder_path" set "destination_folder=%%B"
)

rem 移除路徑中的引號（如果有）
set "source_folder=%source_folder:"=%"
set "destination_folder=%destination_folder:"=%"

rem 確認資料夾路徑是否已設置
if "%source_folder%"=="請輸入來源資料夾路徑" (
    echo 請先在 copypath.ini 中設置來源資料夾路徑。
    echo.
    pause
    exit /b
)
if "%destination_folder%"=="請輸入輸出資料夾路徑" (
    echo 請先在 copypath.ini 中設置輸出資料夾路徑。
    echo.
    pause
    exit /b
)

echo 複製自: "%source_folder%"
echo 複製至: "%destination_folder%"
echo.

if not exist "%source_folder%" (
    echo 來源資料夾 "%source_folder%" 不存在
    echo.
    pause
    exit /b
)

echo 開始複製檔案 ...
echo.
set "fileN=0"
set "folderN=0"

rem 迭代來源資料夾中的檔案
for /r "%source_folder%" %%G in (*) do (
    rem 取得相對路徑
    set "relative_path=%%~dpG"
    rem 移除來源資料夾部分，保留相對路徑
    set "relative_path=!relative_path:%source_folder%\=!"

    rem 設置目標資料夾
    set "dest_dir=%destination_folder%\!relative_path!"

    rem 確保目標資料夾存在
    if not exist "!dest_dir!" (
        mkdir "!dest_dir!"
        set /a folderN+=1
        echo 創建資料夾 "!dest_dir!"
    )

    rem 複製檔案
    set "destination_file=!dest_dir!%%~nxG"
    if not exist "!destination_file!" (
        copy "%%G" "!destination_file!" >nul
        set /a fileN+=1
        echo 複製 %%~nxG 到 "!destination_file!"
    )
)

echo.
echo 已複製來自 "%source_folder%" 的新檔案到 "%destination_folder%"
echo 共創建 %folderN% 個資料夾, %fileN% 個檔案
echo.
echo 程序將在 5 秒後自動關閉...或按任意鍵關閉...
timeout /t 5
exit