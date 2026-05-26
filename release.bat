@echo off
setlocal enabledelayedexpansion

set "MODE="
if "%PYTHON_EXE%"=="" set "PYTHON_EXE=%USERPROFILE%\uv_envs\arm64\uv_312_flappy_dev\Scripts\python.exe"
set "TAG_FLAG="
set "ANY_BRANCH="
set "ALLOW_DIRTY="
set "CREATED_TAG="
set "RELEASE_TAG="
set "RELEASE_VERSION="

:parse_args
if "%~1"=="" goto after_options
if /I "%~1"=="-h" goto show_help
if /I "%~1"=="--help" goto show_help
if /I "%~1"=="help" goto show_help
if /I "%~1"=="--tag" (
    set "TAG_FLAG=--tag"
    shift
    goto parse_args
)
if /I "%~1"=="--any-branch" (
    set "ANY_BRANCH=--any-branch"
    shift
    goto parse_args
)
if /I "%~1"=="--allow-dirty" (
    set "ALLOW_DIRTY=--allow-dirty"
    shift
    goto parse_args
)
if /I "%~1"=="all" goto set_mode
if /I "%~1"=="build" goto set_mode
if /I "%~1"=="send" goto set_mode
if /I "%~1"=="build-pip" goto set_mode
if /I "%~1"=="send-pip" goto set_mode
if /I "%~1"=="build-conda" goto set_mode
if /I "%~1"=="send-conda" goto set_mode
goto usage_error

:set_mode
if defined MODE (
    echo ERROR: multiple release modes supplied: "%MODE%" and "%~1". 1>&2
    goto usage_error
)
set "MODE=%~1"
shift
goto parse_args

:after_options
if not defined MODE set "MODE=build-pip"
if defined ALLOW_DIRTY (
    if /I "%MODE%"=="all" goto allow_dirty_ok
    if /I "%MODE%"=="build" goto allow_dirty_ok
    if /I "%MODE%"=="build-pip" goto allow_dirty_ok
    echo ERROR: --allow-dirty is only supported with build-pip/build/all. 1>&2
    exit /b 2
)
:allow_dirty_ok
if defined ALLOW_DIRTY if defined TAG_FLAG (
    echo ERROR: --allow-dirty cannot be combined with --tag. 1>&2
    exit /b 2
)

if not exist "%PYTHON_EXE%" (
    echo ERROR: could not find executable Python at %PYTHON_EXE% 1>&2
    echo Set PYTHON_EXE to the flapi uv environment's python. 1>&2
    exit /b 1
)

cd /d "%~dp0"

if not defined ANY_BRANCH call :verify_main_branch
if errorlevel 1 exit /b 1
call :maybe_tag
if errorlevel 1 exit /b 1

if /I "%MODE%"=="all" goto build_pip
if /I "%MODE%"=="build" goto build_pip
if /I "%MODE%"=="build-pip" goto build_pip
if /I "%MODE%"=="send" goto send_pip
if /I "%MODE%"=="send-pip" goto send_pip
goto usage_error

:usage
echo Usage: %~nx0 [all^|build^|send^|build-pip^|send-pip] [--tag] [--any-branch] [--allow-dirty]
echo   all/build/build-pip: build pip artifacts locally
echo   send/send-pip: publish pip artifacts with twine
echo   --tag: create and verify a new local git tag before running
echo   --any-branch: skip the main-branch check
echo   --allow-dirty: allow build-pip/build/all from a dirty tree
echo.
echo Environment:
echo   PYTHON_EXE defaults to: %PYTHON_EXE%
exit /b 0

:show_help
call :usage
exit /b 0

:usage_error
call :usage
exit /b 2

:conda_unsupported
echo ERROR: ionbus_flapi has no conda-recipe directory; conda release modes are not supported. 1>&2
exit /b 2

:verify_main_branch
set "CURRENT_BRANCH="
for /f "usebackq delims=" %%I in (`git rev-parse --abbrev-ref HEAD 2^>nul`) do set "CURRENT_BRANCH=%%I"
if /I not "%CURRENT_BRANCH%"=="main" (
    echo ERROR: not on main branch ^(currently on '%CURRENT_BRANCH%'^). 1>&2
    echo Use --any-branch to override. 1>&2
    exit /b 1
)
exit /b 0

:verify_clean_tree
set "DIRTY_TREE="
for /f "usebackq delims=" %%I in (`git status --porcelain`) do set "DIRTY_TREE=1"
if defined DIRTY_TREE (
    echo ERROR: release requires a clean git tree. 1>&2
    git status --short 1>&2
    exit /b 1
)
exit /b 0

:get_tag
set "GIT_DESCRIBE_TAG="
for /f "usebackq delims=" %%I in (`git describe --tags --exact-match 2^>nul`) do set "GIT_DESCRIBE_TAG=%%I"
if not defined GIT_DESCRIBE_TAG (
    echo ERROR: HEAD is not tagged. Re-run with --tag to create a release tag first. 1>&2
    exit /b 1
)
exit /b 0

:verify_tag
call :get_tag
if errorlevel 1 exit /b 1
if not "%~1"=="" (
    if /I not "%GIT_DESCRIBE_TAG%"=="%~1" (
        echo ERROR: expected HEAD tag "%~1" but found "%GIT_DESCRIBE_TAG%" 1>&2
        exit /b 1
    )
)
exit /b 0

:read_project_version
set "RELEASE_VERSION="
for /f "usebackq delims=" %%I in (`"%PYTHON_EXE%" -c "import pathlib, tomllib; print(tomllib.loads(pathlib.Path('pyproject.toml').read_text())['project']['version'])"`) do set "RELEASE_VERSION=%%I"
if not defined RELEASE_VERSION (
    echo ERROR: failed to read project.version from pyproject.toml 1>&2
    exit /b 1
)
exit /b 0

:verify_tag_matches_project_version
set "TAG_NO_V=%RELEASE_TAG%"
if /I "%TAG_NO_V:~0,1%"=="v" set "TAG_NO_V=%TAG_NO_V:~1%"
if /I "%RELEASE_TAG%"=="%RELEASE_VERSION%" exit /b 0
if /I "%TAG_NO_V%"=="%RELEASE_VERSION%" exit /b 0
echo ERROR: pyproject.toml version "%RELEASE_VERSION%" does not match release tag "%RELEASE_TAG%". 1>&2
exit /b 1

:ensure_release_context
if not defined ALLOW_DIRTY (
    call :verify_clean_tree
    if errorlevel 1 exit /b 1
) else (
    echo WARNING: building local test artifact from a dirty tree. 1>&2
)
call :verify_tag
if errorlevel 1 exit /b 1
set "RELEASE_TAG=%GIT_DESCRIBE_TAG%"
call :read_project_version
if errorlevel 1 exit /b 1
call :verify_tag_matches_project_version
if errorlevel 1 exit /b 1
exit /b 0

:cleanup_pip
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
for /d %%D in (*.egg-info) do rmdir /s /q "%%D"
exit /b 0

:maybe_tag
if /I not "%TAG_FLAG%"=="--tag" exit /b 0
call :verify_clean_tree
if errorlevel 1 exit /b 1
set "TAG_OUTPUT="
for /f "usebackq delims=" %%I in (`"%PYTHON_EXE%" -m ionbus_utils.git_utils.auto_tag . --name-only 2^>^&1`) do set "TAG_OUTPUT=%%I"
set "CREATED_TAG=%TAG_OUTPUT%"
if not "!TAG_OUTPUT:tag='=!"=="!TAG_OUTPUT!" (
    for /f "tokens=2 delims='" %%I in ("!TAG_OUTPUT!") do set "CREATED_TAG=%%I"
)
if not defined CREATED_TAG (
    echo ERROR: failed to compute new tag name 1>&2
    exit /b 1
)
git rev-parse -q --verify "refs/tags/%CREATED_TAG%" >nul 2>nul
if not errorlevel 1 (
    echo ERROR: tag "%CREATED_TAG%" already exists locally 1>&2
    exit /b 1
)
git tag -a "%CREATED_TAG%" -m "auto-tag %CREATED_TAG%"
if errorlevel 1 exit /b 1
call :verify_tag "%CREATED_TAG%"
if errorlevel 1 exit /b 1
echo Created local tag: %CREATED_TAG%
exit /b 0

:verify_dist
"%PYTHON_EXE%" -c "import pathlib, sys; version=sys.argv[1]; files=sorted(pathlib.Path('dist').iterdir()) if pathlib.Path('dist').is_dir() else []; wheel=[p for p in files if p.suffix=='.whl' and version in p.name]; sdist=[p for p in files if p.name.endswith('.tar.gz') and version in p.name]; sys.exit(0 if wheel and sdist else 1)" "%RELEASE_VERSION%"
if errorlevel 1 (
    echo ERROR: expected wheel and sdist for version %RELEASE_VERSION% in dist\ 1>&2
    exit /b 1
)
exit /b 0

:verify_built_package_versions
"%PYTHON_EXE%" -c "import email.parser, io, pathlib, sys, tarfile, zipfile; v=sys.argv[1]; wheels=sorted(pathlib.Path('dist').glob(f'*{v}*.whl')); sdists=sorted(pathlib.Path('dist').glob(f'*{v}*.tar.gz')); assert len(wheels)==1, f'expected one wheel, found {len(wheels)}'; assert len(sdists)==1, f'expected one sdist, found {len(sdists)}'; parse=lambda t: email.parser.Parser().parsestr(t)['Version']; z=zipfile.ZipFile(wheels[0]); meta=[n for n in z.namelist() if n.endswith('.dist-info/METADATA')]; assert len(meta)==1, f'expected one METADATA, found {len(meta)}'; wv=parse(z.read(meta[0]).decode('utf-8')); tf=tarfile.open(sdists[0], 'r:gz'); names=tf.getnames(); pkg=[n for n in names if n.count('/')==1 and n.endswith('/PKG-INFO')]; assert len(pkg)==1, f'expected one PKG-INFO, found {len(pkg)}'; member=tf.extractfile(pkg[0]); sv=parse(io.TextIOWrapper(member, encoding='utf-8').read()); assert wv==v, f'wheel version {wv!r} != {v!r}'; assert sv==v, f'sdist version {sv!r} != {v!r}'" "%RELEASE_VERSION%"
if errorlevel 1 (
    echo ERROR: built package metadata verification failed 1>&2
    exit /b 1
)
exit /b 0

:build_pip
call :ensure_release_context
if errorlevel 1 exit /b 1
call :cleanup_pip
"%PYTHON_EXE%" -c "import build"
if errorlevel 1 (
    echo ERROR: Python environment is missing "build". Install it in the flapi uv env. 1>&2
    exit /b 1
)
"%PYTHON_EXE%" -m build --no-isolation --skip-dependency-check
if errorlevel 1 exit /b 1
"%PYTHON_EXE%" -c "import twine"
if errorlevel 1 (
    echo WARNING: twine is not installed; skipping twine check 1>&2
) else (
    "%PYTHON_EXE%" -c "import pathlib, subprocess, sys; files=sorted(str(p) for p in pathlib.Path('dist').glob('*')); sys.exit(subprocess.run([sys.executable, '-m', 'twine', 'check', *files], check=False).returncode if files else 1)"
    if errorlevel 1 exit /b 1
)
call :verify_dist
if errorlevel 1 exit /b 1
call :verify_built_package_versions
if errorlevel 1 exit /b 1
echo Built pip artifacts in: %CD%\dist
echo Version/tag used: %RELEASE_TAG%
exit /b 0

:send_pip
call :ensure_release_context
if errorlevel 1 exit /b 1
call :verify_dist
if errorlevel 1 exit /b 1
call :verify_built_package_versions
if errorlevel 1 exit /b 1
"%PYTHON_EXE%" -c "import twine"
if errorlevel 1 (
    echo ERROR: Python environment is missing "twine". Install it in the flapi uv env. 1>&2
    exit /b 1
)
"%PYTHON_EXE%" -m twine upload dist/*
exit /b %errorlevel%
