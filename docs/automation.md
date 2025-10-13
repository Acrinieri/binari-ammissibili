# Automazione flusso JSON → API → destinazione

Questo progetto espone `POST /tracks/suggestions`, endpoint che accetta un payload JSON e restituisce le alternative calcolate.  
Per integrare l'applicazione in una pipeline automatica è disponibile lo script `scripts/json_pipeline.py`.

## Requisiti

- Python 3.10+
- Dipendenze già elencate in `requirements.txt` (`requests` viene installato con il resto dell'app)

## Utilizzo

```bash
python -m scripts.json_pipeline \
  --input /percorso/al/file/input.json \
  --api-url http://127.0.0.1:8000/tracks/suggestions \
  --forward-url https://altra-app.example.com/hook \
  --output-path /tmp/output.json
```

- `--input` (obbligatorio): file JSON con il payload da inviare. Deve rispettare lo schema `SuggestionRequest`.
- `--api-url` (opzionale): endpoint FastAPI. Default `http://127.0.0.1:8000/tracks/suggestions`.
- `--forward-url` (opzionale): URL dell'altra applicazione; lo script esegue un `POST` con il JSON di risposta.
- `--output-path` (opzionale): se specificato, salva la risposta anche su file (utile per logging o audit).
- `--timeout` (opzionale): timeout in secondi per le chiamate HTTP (default `10`).

Lo script genera un file con struttura `{"trains": [...]}`; ogni elemento contiene i campi richiesti (`train_code`, `train_length_m`, `train_category`, `planned_track`, `is_prm`).

Il servizio accetta sia il formato singolo (campi `train_code`, `train_length_m`, ecc.) sia un array `trains` di oggetti con le stesse proprietà. Lo script `generate_input` continua a produrre il payload singolo, ma puoi creare input batch scrivendo manualmente un file come:

```json
{
  "trains": [
    {
      "train_code": "61234",
      "train_length_m": 250,
      "train_category": "IC",
      "planned_track": "IV",
      "is_prm": false
    },
    {
      "train_code": "98765",
      "train_length_m": 320,
      "train_category": "INV",
      "planned_track": null,
      "is_prm": false
    }
  ]
}
```

## Job automatico (cron/systemd)

Per il deploy su Linux è disponibile lo script `scripts/pipeline_job.sh`, che:

1. genera l'input tramite `scripts.generate_input` usando le variabili d'ambiente;
2. invoca `scripts.json_pipeline` e salva il risultato in `runtime/response.json`;
3. inoltra il JSON alla seconda applicazione se `FORWARD_URL` è impostata.

Variabili supportate:

| Variabile | Default | Descrizione |
| --- | --- | --- |
| `TRAIN_CODE` | `12345` | Codice del treno. |
| `TRAIN_LENGTH` | `250` | Lunghezza in metri. |
| `TRAIN_CATEGORY` | `REG` | Categoria del treno. |
| `PLANNED_TRACK` | *(vuoto)* | Binario previsto; se vuoto viene inviato `null`. |
| `IS_PRM` | `false` | Usa `"true"` per attivare il flag PRM. |
| `TRACKS_OVERRIDE_FILE` | *(vuoto)* | Percorso dataset alternativo (opzionale). |
| `API_URL` | `http://127.0.0.1:8000/tracks/suggestions` | Endpoint FastAPI. |
| `FORWARD_URL` | *(vuoto)* | Endpoint dell’applicazione ricevente (POST). |
| `INPUT_PATH` | `<repo>/runtime/request.json` | Dove salvare l’input generato. |
| `OUTPUT_PATH` | `<repo>/runtime/response.json` | Dove salvare la risposta. |
| `TIMEOUT` | `10` | Timeout HTTP in secondi. |

Esempio di esecuzione manuale:

```bash
cd /srv/binari/backend-fastapi
TRAIN_CODE=98765 TRAIN_LENGTH=320 TRAIN_CATEGORY=IC \
FORWARD_URL=https://downstream.example.com/ingest \
bash scripts/pipeline_job.sh
```

### Installazione cron

1. Assicurarsi che l’ambiente Python virtuale sia presente in `.venv/`.
2. Rendere eseguibili gli script: `chmod +x scripts/pipeline_job.sh scripts/pipeline_job_cron.sh`.
3. Utilizzare il wrapper `scripts/pipeline_job_cron.sh`, che attiva automaticamente il venv e richiama `pipeline_job.sh`.
4. Aggiungere la voce cron, ad esempio ogni 15 minuti:

```
*/15 * * * * cd /srv/binari/backend-fastapi && \
  TRAIN_CODE=98765 TRAIN_LENGTH=320 TRAIN_CATEGORY=IC \
  FORWARD_URL=https://downstream.example.com/ingest \
  /bin/bash scripts/pipeline_job_cron.sh >> /var/log/binari_pipeline.log 2>&1
```

In alternativa è possibile usare un servizio `systemd` o un orchestratore (Airflow, Prefect) seguendo gli stessi comandi di base.

### Ambienti Docker

Se l'app gira in container, esegui gli script tramite `docker compose exec backend ...`, ad esempio:

```bash
docker compose exec backend bash -lc \
  'cd /app && bash scripts/pipeline_job.sh'
```

Per il cron sull'host:

```
*/15 * * * * cd /srv/binari && \
  docker compose exec -T backend bash -lc \
    "cd /app && TRAIN_CODE=98765 TRAIN_LENGTH=320 TRAIN_CATEGORY=IC \
     FORWARD_URL=https://downstream.example.com/ingest \
     bash scripts/pipeline_job.sh" \
  >> /var/log/binari_pipeline.log 2>&1
```

## Possibili integrazioni

- **Cron/Batch**: crea un job che aggiorna periodicamente `input.json` e invoca lo script.
- **CI/CD**: inserisci lo script in una pipeline per validare dataset e pubblicare risultati.
- **Queue/Eventi**: avvolgi lo script in un worker (es. Celery, systemd timer) che risponde a nuovi file o messaggi.

In caso di errori lo script esce con codice diverso da zero e riporta la causa (file mancante, payload non valido, API che risponde con errore, ecc.). Integralo con il tuo sistema di monitoraggio per gestire retry e alert.
