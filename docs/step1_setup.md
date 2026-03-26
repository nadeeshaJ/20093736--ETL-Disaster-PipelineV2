# Step 1 – Azure VM Project Setup

In this step, the ETL project repository was prepared inside the Azure VM environment.

## Tasks completed
- Verified Git repository status
- Created ETL folder structure
- Started terminal session recording using `script`
- Created Python virtual environment
- Installed required Python packages
- Generated `requirements.txt`
- Added `.gitignore`
- Created base project files

## Main commands used

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install pandas requests openpyxl python-dotenv pytest
pip freeze > requirements.txt
