Local test setup for Library-Inventory-system

Prerequisites
- Python 3.10+ (Windows)

Install dependencies (PowerShell):

```powershell
pip install -r requirements.txt
```

Run a simple mock backend (for testing):

```powershell
python mock_backend.py
```

Start the frontend GUI (in a separate terminal):

```powershell
python "c:\Users\nihal\OneDrive\Documents\Library-Inventory-system\frontend (1).py"
```

Notes
- The mock backend runs on `http://127.0.0.1:5000` and implements the endpoints the frontend expects:
  - `GET /media` (returns a list)
  - `GET /media/category/<category>`
  - `GET /media/search/<name>`
  - `POST /media/create` (JSON body)
  - `DELETE /media/delete/<id>`

- The frontend script `frontend (1).py` has a `main()` guard so it can be imported without launching the GUI.
- If you have an actual backend, stop the mock server before starting the real backend.
