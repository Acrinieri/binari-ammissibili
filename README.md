# Binari Ammissibili

FastAPI + React application that suggests admissible railway tracks for a train based on configurable rules and a persistent dataset.

## Features

- Encapsulates the selection rules from the original CLI script into a REST API.
- Stores tracks inside a SQLite database (`tracks.db`), seeded from `app/data/tracks.json` on first launch.
- Provides `POST /tracks/suggestions` to calculate up to seven alternative tracks, returning a reason for each choice.
- Stores category-specific rules and priority criteria in the database, editable from the admin UI (with one-click fallback to defaults).
- React interface to input train details, review the dataset, and administer both tracks and matching rules (create/update/delete/reset).

## Getting Started

1. **Clone and enter the project**
   ```bash
   git clone https://github.com/Acrinieri/binari-ammissibili.git
   cd binari-ammissibili
   ```

2. **Backend (FastAPI)**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate          # Windows
   # source .venv/bin/activate     # macOS / Linux
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```
   The API listens on `http://127.0.0.1:8000`. The first startup creates `tracks.db` and imports the sample data if the database is empty.

3. **Frontend (React)**
   ```bash
   cd frontend-react
   npm install
   npm start
   ```
The UI runs on `http://localhost:3000` and calls the FastAPI server.

## Deployment

- Production compose stack (backend + frontend) is configured for `https://rfi.b4service.it` (UI) and `https://api.rfi.b4service.it` (API).
- The stack plugs into the existing `service-tier` Docker network alongside `nginx-proxy`.
- The full sysadmin run-book is available in [`docs/deploy.md`](docs/deploy.md).

## API Overview

| Endpoint | Method | Description |
| --- | --- | --- |
| `/health` | `GET` | Liveness check. |
| `/tracks` | `GET` | Returns the current dataset of tracks (dictionary keyed by name). |
| `/tracks/suggestions` | `POST` | Accepts train data and returns up to seven admissible tracks with explanations. |
| `/admin/tracks` | `GET` | Lists all tracks (id + details) for the admin interface. |
| `/admin/tracks` | `POST` | Creates a new track. |
| `/admin/tracks/{id}` | `PUT` | Updates an existing track. |
| `/admin/tracks/{id}` | `DELETE` | Removes a track. |
| `/admin/config/category-rules` | `GET` | Lists effective rules per train category (custom + defaults). |
| `/admin/config/category-rules/{category}` | `PUT` | Creates or updates the rule for a specific category. |
| `/admin/config/category-rules/{category}` | `DELETE` | Removes the custom rule so defaults apply again. |
| `/admin/config/priority-configs` | `GET` | Lists ordering/weights applied during sorting per category. |
| `/admin/config/priority-configs/{category}` | `PUT` | Saves a custom set of criteria/weights for a category. |
| `/admin/config/priority-configs/{category}` | `DELETE` | Removes the custom profile and reverts to defaults. |

Sample payload (single train):

```json
{
  "train_code": "12345",
  "train_length_m": 250,
  "train_category": "IC",
  "planned_track": "IV",
  "is_prm": false
}
```

Sample response:

```json
{
  "alternatives": [
    {
      "track": "III",
      "reason": "Marciapiede da 449 m >= lunghezza treno 250 m. Fascia prioritaria per lunga percorrenza (2-13). Adiacente al binario previsto. Marciapiede identico al previsto. Disponibile marciapiede alto."
    }
  ]
}
```

È anche possibile inviare più treni in un'unica richiesta usando il campo `trains`:

```json
{
  "trains": [
    {
      "train_code": "12345",
      "train_length_m": 250,
      "train_category": "IC",
      "planned_track": "IV",
      "is_prm": false
    },
    {
      "train_code": "67890",
      "train_length_m": 210,
      "train_category": "REG",
      "planned_track": null,
      "is_prm": false
    }
  ]
}
```

In questo caso la risposta includerà `items`, una voce per ogni treno elaborato, mentre il campo `alternatives` rimane per compatibilità con richieste singole.

## Customising the Dataset

- Usa la sezione “Gestione binari” dell’interfaccia React per aggiungere, modificare o eliminare binari: le modifiche vengono salvate subito nel database.
- In alternativa puoi chiamare direttamente gli endpoint `/admin/tracks` mostrati sopra (ad es. per script di automazione).
- Il file `app/data/tracks.json` resta come seed iniziale: viene letto solo se il database non contiene record.
- Per test o simulazioni veloci puoi ancora inviare un dataset ad hoc tramite il campo `tracks_override` della richiesta a `/tracks/suggestions`.

## Frontend Notes

- The form supports train classes such as `REG`, `IC`, `ES*`, `FR`, `INV`, etc.
- Setting the PRM flag forces the logic to apply PRM-specific exclusions.
- Results are shown in the order returned by the service, already sorted by the ranking rules from the legacy script.

## Next Steps

- Proteggere gli endpoint di amministrazione con autenticazione/autorizzazione prima di esporre il servizio.
- Valutare una migrazione a Postgres o altra base dati condivisa se servono ambienti multi‑utente o alta concorrenza.
- Automatizzare verifiche (lint, type checking, test end-to-end) con GitHub Actions prima di distribuire il servizio.
- Integrare pipeline automatiche usando lo script `python -m scripts.json_pipeline` descritto in [`docs/automation.md`](docs/automation.md).





