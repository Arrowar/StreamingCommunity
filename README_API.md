# StreamingCommunity — API HTTP (FastAPI)

Questo documento spiega come usare l'API HTTP esposta. È pensato per chi vuole integrare [StreamingCommunity](https://github.com/Arrowar/StreamingCommunity) in un'app, script o interfaccia grafica.

Troverai esempi pratici (curl e Python), risposte esempio, note di configurazione e suggerimenti per risolvere errori comuni.

> [!NOTE]
> L'API deve essere abilitata nel file `config.json` impostando `DEFAULT.expose_http_api` a `true`. La documentazione interattiva è disponibile su `/docs` quando il server è in esecuzione.

> [!IMPORTANT]
> Quando `DEFAULT.expose_http_api` è impostato su `true` l'applicazione verrà eseguita in modalità non-interattiva _(server-only mode)_: la console mostrerà comunque le informazioni come di consueto ma l'input della tastiera e tutte le attività interattive saranno disabilitate. Potrai inviare comandi esclusivamente dagli endpoint che l'API offre.
> 
> L'unica interazione disponibile è Ctrl+C per fermare l'applicazione.

----

## Concetti chiave

- `module`: il provider (cartella in `StreamingCommunity/Api/Site/<module>`). Esempio: `streamingcommunity`, `altadefinizione`.
- `action`: l'operazione da eseguire su un module (es. `download_film`, `download_series` oppure una funzione custom esposta).
- `item`: oggetto risultato di una ricerca (dizionario). Contiene i campi che il provider fornisce (`id`, `name`, `url`, `type`, `image`, ecc.).
- `selections`: parametri opzionali per i download di serie (es. `{"season":"2","episode":"1-5"}`).
- `job`: unità di lavoro messa in coda; gestita dal `JobManager` e processata in ordine FIFO, una alla volta.

----

## Endpoints principali

- `GET /providers`: elenca i provider caricati.
- `POST /search`: esegue una ricerca.
- `POST /module_call`: invoca una funzione di un module (sync o background).
- `POST /jobs`: crea un job per eseguire un'azione (download).
- `GET /jobs`: mostra la lista dei job attivi.
- `GET /jobs/{job_id}`: dettagli e stato di un job.

Tutte le chiamate possono essere protette con Basic Auth se sono state inserite `http_api_username` e `http_api_password` in `config.json`.

> [!TIP]
> Dopo aver letto questo documento ti consiglio di mettere le mani in pasta e provare l'API in http://localhost:8080/docs. 

----

## Config utili

- `DEFAULT.expose_http_api`: `true|false`  abilita/disabilita l'API.
- `DEFAULT.http_api_port`: porta su cui esporre l'API (es. `8080`).
- `DEFAULT.http_api_username`, `DEFAULT.http_api_password`: credenziali Basic Auth (opzionali).
- `DEFAULT.http_api_provider_timeout`: tempo in secondi per chiamate verso i provider (default: 20).

> [!IMPORTANT]
> Prima di usare i download assicurati che i provider da cui vuoi scaricare non richiedano credenziali o configurazioni addizionali. Alcuni provider possono restituire errori se non configurati correttamente.

> [!NOTE]
> Se non hai modificato le impostazioni dell'API, all'avvio sarà esposta all'indirizzo http://localhost:8080/.

----

## 1) Elenco provider

#### Richiesta curl

```
curl http://127.0.0.1:8080/providers
```

##### Risposta (esempio)

```json
{
  "providers": [
    {"name":"streamingcommunity","indice":0,"use_for":"Film_&_Serie"},
    {"name":"altadefinizione","indice":2,"use_for":"Film_&_Serie"}
  ]
}
```

----

## 2) Ricerca contenuti

Esempi di richieste:

#### curl

```
curl -X POST http://127.0.0.1:8080/search \
  -H 'Content-Type: application/json' \
  -d '{"provider":"all","query":"Matrix"}'
```

#### Python (httpx)

```py
import httpx
client = httpx.Client(timeout=60.0)
r = client.post('http://127.0.0.1:8080/search', json={'provider':'all','query':'Matrix'})
print(r.json())
```

##### Risposta (esempio semplificato)

```json
{
  "query": "Matrix",
  "results": {
    "streamingcommunity": [ {"id":1994,"name":"Matrix","type":"movie","url":"..."} ],
    "altadefinizione": [ {"name":"Matrix Reloaded","type":"movie","url":"..."} ],
    "crunchyroll": {"error":{"type":"ValueError","message":"Please enter a correct 'etp_rt' value"}}
  }
}
```

Note

- Se un provider fallisce viene restituito un oggetto `error` per quel provider; gli altri provider continuano a rispondere.
- Usa i risultati di `/search` come `item` per creare job di download.

----

## 3) Chiamare funzioni del module (module_call)

Usa `module_call` per invocare funzioni esposte o metodi noti del provider.

##### Richiesta sincrona

```
POST /module_call
{
  "module": "streamingcommunity", # Provider 'streamingcommunity'
  "function": "search", # Nome funzione da eseguire
  "kwargs": {"string_to_search":"Matrix","get_onlyDatabase":true},
  "background": false
}
```

##### Risposta (sync success)

```json
{ "result": {...} }
```

##### Schedulazione come job

```
POST /module_call
{ ... , "background": true }
```

##### Risposta

```json
{ "status": "scheduled", "job_id": 5 }
```

----

## 4) Job: creare e controllare un download

### Creare job

##### Esempio di download (film):

```
POST /jobs
{
  "module":"streamingcommunity",
  "action":"download_film",
  "item": { /* item preso da /search */ }
}
```

##### Risposta

```json
{ "job_id": 12 }
```

##### Controllare lo stato

```
GET /jobs/12
```

### Tipi di risposte (esempi)

queued

```json
{ "id":12, "status":"queued", "created_at": 1690000000.0 }
```

running

```json
{ "id":12, "status":"running", "started_at":1690000005.0 }
```

finished

```json
{ "id":12, "status":"finished", "finished_at":1690000100.0, "result": "..." }
```

failed

```json
{ "id":12, "status":"failed", "error":"ValueError: missing stream url" }
```

### Selezioni (`selections`)

Come determinare la struttura effettiva di `selections`:

- **Controlla il provider**: la struttura valida dipende dal provider (cartella in `StreamingCommunity/Api/Site/<provider>`). Molti provider usano le chiavi `season` e `episode`.
- **Guarda il codice**: cerca dove il provider legge `selections` (es. `selections.get('season')`, `selections.get('episode')`).
- **Esempi pratici**: usa una richiesta `/search` o leggi il codice del provider per capire quali chiavi accetta.

Tipicamente per le serie il formato usato è:

```json
"selections": {
  "season": "1",
  "episode": "1-5"
}
```

##### Creare un job per scaricare una serie (stagione 1, episodi 1-5)

```
POST /jobs
{
  "module": "streamingcommunity",
  "action": "download_series",
  "item": { /* item preso da /search, es. {"id":123, "name":"My Show", "url":"..."} */ },
  "selections": { "season": "1", "episode": "1-5" }
}
```

##### Risposta (job creato con successo)

```json
{ "job_id": 42 }
```

Poi `GET /jobs/42` tipicamente restituisce qualcosa del genere (il campo `payload` mantiene le informazioni inviate):

```json
{
  "id": 42,
  "progress": 0,
  "status": "queued",
  "created_at": 1690000000.0,
  "payload": {
    "module": "streamingcommunity",
    "action": "download_series",
    "item": {"id":123,"name":"My Show","url":"..."},
    "selections": {"season":"1","episode":"1-5"}
  }
}
```

Se un provider richiede parametri diversi, il job conterrà quelle chiavi; per dubbi controlla il file `StreamingCommunity/Api/Site/<provider>/__init__.py`.


> [!NOTE]
> Se farai più richieste download: i job sono eseguiti uno alla volta (sequenziale). Pollare lo stato con `GET /jobs/{id}` è la pratica raccomandata.

> [!IMPORTANT]
> L'oggetto `job` che restituisce `GET /jobs` e `GET /jobs/{id}` contiene il campo `progress` (0..100). Questo valore rappresenta il progresso **totale** del _job_ (dall'inizio del download fino alla fase di unione audio/video). Nei providers si possono aggiustare i valori percentuali rappresentati durante il processo utilizzando `JOB_MANAGER.update_progress(percent)` dal codice di ognuno di essi.

----

## 5) Esporre una funzione di provider (expose_api)

Obiettivo: esporre una funzione custom nel module _aka provider (es. `/Api/Site/raiplay/`)_ e poterla chiamare via `module_call` o come job.

1. Apri il file del provider (es. `StreamingCommunity/Api/Site/mymodule/__init__.py` o altro file in quella cartella).
2. Aggiungi:

```py
from StreamingCommunity.Api.http_api import expose_api

@expose_api('my_custom')
def my_custom(item, selections=None, **kwargs):
    # item è un oggetto MediaItem (puoi leggere item.name, item.url ecc.)
    # fai il lavoro e ritorna un risultato serializzabile
    # Durante operazioni lunghe puoi aggiornare il progresso totale del job
    # (0..100) così il client che sta pollando `/jobs/{id}` ottiene feedback.
    from StreamingCommunity.Api.http_api import JOB_MANAGER
    JOB_MANAGER.update_progress(5)
    # ... avvia il download ...
    JOB_MANAGER.update_progress(60)
    # ... sincronizza audio/video ...
    JOB_MANAGER.update_progress(95)
    return {'status':'ok','title': getattr(item,'name',None)}
```

3. Riavvia lo script per ricaricare i moduli.
4. Test via API (sync):

```
POST /module_call
{
  "module":"mymodule",
  "function":"my_custom",
  "kwargs": {"item": {/* item JSON preso da /search */}},
  "background": false
}
```

Risposta (esempio)

```json
{ "result": {"status":"ok","title":"Matrix"} }
```

> [!IMPORTANT]
> Seleziona nomi univoci per `expose_api('name')` per evitare conflitti tra moduli.

----

## Errori comuni e come risolverli

#### 1. `401 Unauthorized` credenziali mancanti o sbagliate
Impostare header `Authorization: Basic <base64(user:pass)>` o rimuovere le credenziali da `config.json`.

#### 2. `Timeout` su `/search` per un provider
Aumentare `DEFAULT.http_api_provider_timeout` o correggere il provider che richiede input.

#### 3. `job failed`
Leggere `GET /jobs/{id}` campo `error` per capire cosa non ha funzionato (es. mancanza di campi in `item`, login richiesto, ecc.).

#### 4. `module not found`
Controllare `GET /providers` per il nome corretto del module.

----

## Buone pratiche di integrazione

- Usa i risultati di `/search` come `item` senza modificarli salvo campo specifici necessari.
- Per serie, passare `selections` chiare (`season`/`episode` o range `1-5`).
- Non fare affidamento su chiamate sincrone per download lunghi: usa `POST /jobs` e polla lo stato.
- Proteggi l'API in produzione con Basic Auth o con altro strato di autenticazione più forte.

----

## Esempi Python rapidi (httpx)

```py
import httpx
client = httpx.Client(timeout=60.0)

# search
r = client.post('http://127.0.0.1:8080/search', json={'provider':'all','query':'Matrix'})
print(r.json())

# create job (supponendo item sia ottenuto dalla search)
item = r.json()['results']['streamingcommunity'][0]
job = client.post('http://127.0.0.1:8080/jobs', json={'module':'streamingcommunity','action':'download_film','item':item})
print(job.json())

# poll
job_id = job.json()['job_id']
while True:
    s = client.get(f'http://127.0.0.1:8080/jobs/{job_id}').json()
    print(s['status'])
    if s['status'] in ('finished','failed'):
        break
    import time; time.sleep(1)
```

----

## Manca qualcosa?

Se trovi un provider che necessita modifiche per l'uso via API (es. firma funzione non standard, input interattivo), apri una issue o invia una PR con la correzione.

Se pensi che questo documento abbia bisogno di informazioni aggiornate, corrette od organizzate diversamente, invia una PR.

Se invece vuoi contribuire in qualsiasi modo: sei il benvenuto.

## TODO (in ordine di importanza)
- [ ] Migliorare il progress system, attualmente è implementato in modo molto spartano.
- [ ] Rendere più efficiente la gestione degli errori e validation. Attualmente molto codice è ripetuto.
- [ ] Implementare SSE invece di utilizzare Job Polling. Più efficiente, più pulito, ma più complesso da gestire (non solo per chi deve implementarlo, ma anche per chi consuma l'API).

