# WSL and VS Code setup

Preparation only, checked 4 November 2026. The workspace is:

- Windows: `C:\Users\ASUS\OneDrive\Desktop\nasa`
- WSL: `/mnt/c/Users/ASUS/OneDrive/Desktop/nasa`
- Linux learning venv: `/home/asus/.venvs/agroshift-prep`

The workspace stays where the user opened it. The virtual environment lives on
Linux storage to avoid syncing thousands of dependency files through OneDrive.
No final application repository or GitHub remote has been created.

## Already done on this computer

WSL2 Ubuntu-26.04 starts successfully. Python 3.14.4, Git 2.53.0 and Windows
VS Code's launcher are available. The isolated venv and dependencies have been
installed. Imports, `pip check` and the built-in Streamlit hello health endpoint
passed. The temporary verification server was stopped.

## Open the existing environment

In Windows PowerShell:

```powershell
wsl -d Ubuntu-26.04
```

Then inside Ubuntu:

```bash
cd /mnt/c/Users/ASUS/OneDrive/Desktop/nasa
source /home/asus/.venvs/agroshift-prep/bin/activate
python --version
python -m pip check
code .
```

If the VS Code WSL extension is missing, run this in Windows PowerShell, then
open the folder again from Ubuntu:

```powershell
code --install-extension ms-vscode-remote.remote-wsl
```

In the WSL VS Code window, install Microsoft's Python extension in WSL if needed.
Use **Python: Select Interpreter → Enter interpreter path** and choose:

```text
/home/asus/.venvs/agroshift-prep/bin/python
```

The extension installation and interactive editor selection were not performed
by this session. The launcher was detected, not visually inspected.

## Recreate the learning environment if necessary

In Ubuntu, from the workspace:

```bash
python3 -m venv ~/.venvs/agroshift-prep
source ~/.venvs/agroshift-prep/bin/activate
python -m pip install -r preparation/requirements.lock.txt
python -m pip check
```

If `venv` or the supporting tools are absent on a different Ubuntu installation:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git curl
```

That system-package command is a conditional setup instruction, not a command
executed in this session. The lock file was generated on Python 3.14/Linux.
For another Python version or operating system, resolve `requirements.in` in a
separate venv and verify it rather than assuming the same lock is compatible.
At deployment, match local Python to an available cloud runtime and rerun checks.

## Learning checks

From the activated venv:

```bash
python preparation/power_access_exercise.py
python -m streamlit hello --server.headless true
```

For the hello example, open the URL printed by Streamlit, normally
`http://localhost:8501`. Press Ctrl+C to stop it. This is Streamlit's own example,
not AgroShift AI. The NASA exercise overwrites its three named sample files and
its manifest with newly retrieved evidence. It sends only public demonstration
coordinates, dates and parameter names, and needs no API key.

The original successful outputs are in `preparation/evidence/`. Each location
contains seven days × six parameter values (42), with 126 total returned values.
The exercise verifies HTTP success, required fields, dates, finite non-fill
values and reads unit metadata. It does not validate agronomic accuracy.

After learning-library changes, produce a new lock only after checks succeed:

```bash
python -m pip freeze > preparation/requirements.lock.txt
```

## Running the AgroShift AI Application and Test Suite

From the activated venv in `/mnt/c/Users/ASUS/OneDrive/Desktop/nasa`:

```bash
python -m pytest -v
./scripts/run.sh
```

Or on Windows, double-click `START_AGROSHIFT.cmd`.

Sources: [Streamlit installation](https://docs.streamlit.io/get-started/installation/command-line),
[VS Code WSL documentation](https://code.visualstudio.com/docs/remote/wsl).
