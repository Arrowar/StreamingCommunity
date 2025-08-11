# Git Hooks Template

Questa cartella contiene i template per i git hooks utilizzati nel progetto StreamingCommunity.

## 🚀 Configurazione Rapida

Per attivare gli hooks in questo repository, esegui:

```bash
# Configura Git per utilizzare la cartella .githooks
git config core.hooksPath .githooks/templates

# Oppure copia gli hooks nella cartella .git/hooks
cp .githooks/templates/* .git/hooks/
```

## 📋 Hooks Disponibili

### Pre-commit Hook

Il pre-commit hook esegue automaticamente i controlli di qualità del codice prima di ogni commit:

- **Controllo Linting**: Esegue `ruff check` sui file Python modificati
- **Controllo Formattazione**: Verifica la formattazione con `ruff format --check`
- **Blocco Commit**: Impedisce il commit se ci sono errori di linting o formattazione

#### Caratteristiche:

✅ **Output colorato** per una migliore leggibilità  
✅ **Controlli solo sui file modificati** per maggiore velocità  
✅ **Suggerimenti automatici** per risolvere i problemi  
✅ **Messaggi di errore chiari** con comandi di risoluzione  

#### Cosa fa:

1. Controlla se `ruff` è installato
2. Identifica i file Python modificati (staged)
3. Esegue `ruff check` per il linting
4. Esegue `ruff format --check` per la formattazione
5. Blocca il commit se ci sono errori e mostra come risolverli

## 🛠️ Installazione Manuale

### Metodo 1: Configurazione globale del repository

```bash
# Imposta la cartella degli hooks per questo repository
git config core.hooksPath .githooks/templates
```

### Metodo 2: Copia nella cartella .git/hooks

```bash
# Copia tutti gli hooks
cp .githooks/templates/* .git/hooks/

# Oppure copia solo il pre-commit hook
cp .githooks/templates/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

## 🔧 Prerequisiti

Assicurati di avere `ruff` installato:

```bash
# Installa ruff
pip install ruff

# Oppure installa tutte le dipendenze del progetto
pip install -r requirements.txt
```

## 📖 Utilizzo

Una volta configurato, l'hook si attiverà automaticamente ad ogni `git commit`:

```bash
# Esempio di commit con hook attivo
git add .
git commit -m "feat: aggiungi nuova funzionalità"

# Output dell'hook:
# ℹ️  INFO: Controllo dei file Python con ruff...
# 🔍 Esecuzione di ruff check...
# 🎨 Controllo formattazione con ruff format...
# ✅ SUCCESSO: Tutti i controlli di ruff sono passati!
# ℹ️  INFO: Procedendo con il commit...
```

## ⚠️ Risoluzione Problemi

Se l'hook blocca il commit, vedrai messaggi come:

```bash
❌ ERRORE: ruff check ha trovato degli errori!

Per correggere automaticamente gli errori risolvibili, esegui:
  ruff check --fix .
  ruff format .
```

### Comandi utili per risolvere i problemi:

```bash
# Corregge automaticamente gli errori di linting
ruff check --fix .

# Formatta tutto il codice
ruff format .

# Esegue entrambi i comandi
ruff check --fix . && ruff format .

# Dopo aver risolto i problemi
git add .
git commit -m "fix: risolvi problemi di linting"
```

## 🚫 Bypass dell'Hook (Non Raccomandato)

In casi eccezionali, puoi bypassare l'hook con:

```bash
git commit --no-verify -m "commit senza controlli"
```

**⚠️ Attenzione**: Questo non è raccomandato in quanto salta tutti i controlli di qualità del codice.

## 🔄 Aggiornamento degli Hooks

Per aggiornare gli hooks:

```bash
# Se usi core.hooksPath, gli hooks si aggiornano automaticamente
git pull

# Se hai copiato gli hooks in .git/hooks, devi aggiornarli manualmente
cp .githooks/templates/* .git/hooks/
```

## 📝 Personalizzazione

Puoi personalizzare gli hooks modificando i file nella cartella `.githooks/templates/`. 

Per esempio, per modificare il pre-commit hook:

1. Modifica `.githooks/templates/pre-commit`
2. Se usi il metodo di copia, ricopia l'hook: `cp .githooks/templates/pre-commit .git/hooks/pre-commit`

## 🤝 Contribuire

Se vuoi aggiungere nuovi hooks o migliorare quelli esistenti:

1. Crea il nuovo hook in `.githooks/templates/`
2. Rendilo eseguibile: `chmod +x .githooks/templates/nome-hook`
3. Aggiorna questo README con la documentazione
4. Testa l'hook prima di fare il commit

## 📚 Riferimenti

- [Git Hooks Documentation](https://git-scm.com/book/en/v2/Customizing-Git-Git-Hooks)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Pre-commit Hooks Best Practices](https://pre-commit.com/)
