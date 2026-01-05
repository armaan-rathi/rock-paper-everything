# Rock Paper Everything

A roguelike Rock–Paper–Scissors web app built with Flask + React.

## Development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

The backend serves the game API at `http://localhost:5001/api`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:5173` and proxies API calls to the backend.

## Data

By default, the backend loads objects from `backend/data/objects.csv`. To use an Excel file, set:

```bash
export OBJECTS_FILE=/path/to/objects.xlsx
```

The file should contain a header row with `name,type`, and each row should map to `rock`, `paper`, or `scissors`.
