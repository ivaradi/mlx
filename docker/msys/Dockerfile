#escape=`
FROM mcr.microsoft.com/windows/servercore:1809
SHELL ["powershell", "-Command"]

RUN $WebClient = New-Object System.Net.WebClient ; `
    $WebClient.DownloadFile('https://www.7-zip.org/a/7z1900-x64.msi', '7z.msi') ; `
    $WebClient.DownloadFile('http://repo.msys2.org/distrib/msys2-x86_64-latest.tar.xz', 'msys2.tar.xz') ; `
    Start-Process msiexec.exe -ArgumentList '/i C:\7z.msi /qn reboot=r' -Wait -PassThru -Verbose ; `
    Start-Process 'C:\Program Files\7-Zip\7z.exe' -ArgumentList 'x msys2.tar.xz' -Wait -PassThru -Verbose ; `
    Start-Process tar -ArgumentList 'xf msys2.tar' -Wait -PassThru -Verbose ; `
    Start-Process msiexec.exe -ArgumentList '/x C:\7z.msi /qn reboot=r' -Wait -PassThru -Verbose ; `
    Remove-Item msys2.tar ; `
    Remove-Item msys2.tar.xz ; `
    Remove-Item 7z.msi

RUN $env:MSYSTEM='MINGW32'  ; `
    C:\msys64\usr\bin\bash.exe --login -c /usr/bin/true.exe ; `
    C:\msys64\usr\bin\pacman.exe -Syu --noconfirm ; `
    C:\msys64\usr\bin\pacman.exe -Su --noconfirm ; `
    C:\msys64\usr\bin\pacman.exe -Scc --noconfirm

COPY setup.sh  C:\msys64\build\

RUN $env:MSYSTEM='MINGW32'; `
    C:\msys64\usr\bin\bash.exe --login -c /build/setup.sh

COPY build.bat build.sh pywin32.patch pywin32git.patch cef_binary_3.3359.1774.gd49d25f_windows32.patch cefpython-66.0.patch py2exe.patch id_rsa C:\msys64\build\

CMD ["powershell.exe"]
