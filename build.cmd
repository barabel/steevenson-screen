@echo off
rem build.cmd       - run the Progon
rem build.cmd test  - run unittest tests
rem FREECAD_CMD overrides the path to freecadcmd.exe.
rem Keep this file ASCII-only: cmd breaks on UTF-8 text.
setlocal
if not defined FREECAD_CMD set "FREECAD_CMD=C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe"
if not exist "%FREECAD_CMD%" (
  echo freecadcmd not found: "%FREECAD_CMD%". Set FREECAD_CMD to freecadcmd.exe. 1>&2
  exit /b 1
)
pushd "%~dp0"

rem Code goes through -c, not as a script path: freecadcmd runs a script file
rem twice and exits with 0 on an exception.
rem Piped stdout defaults to cp1251 (PYTHONIOENCODING is ignored), so force utf-8.
set "INIT=import sys; sys.stdout.reconfigure(encoding='utf-8'); sys.stderr.reconfigure(encoding='utf-8'); sys.path.insert(0, 'src')"
if "%~1"=="test" (
  "%FREECAD_CMD%" -c "%INIT%; import unittest; p = unittest.main(module=None, argv=['build.cmd test', 'discover', '-s', 'tests'], exit=False); sys.exit(not p.result.wasSuccessful())"
) else (
  "%FREECAD_CMD%" -c "%INIT%; import build; build.main()"
)
set "RC=%ERRORLEVEL%"

popd
exit /b %RC%
