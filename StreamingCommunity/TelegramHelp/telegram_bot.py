# 04.02.26
# Made by: @GiuPic

import os
import re
import sys
import time
import uuid
import json
import threading
import subprocess
from typing import Optional

# External libraries
import telebot

session_data = {}

class TelegramSession:

    def set_session(value):
        session_data['script_id'] = value

    def get_session():
        return session_data.get('script_id', 'unknown')

    def updateScriptId(screen_id, titolo):
        json_file = "../../scripts.json"
        try:
            with open(json_file, 'r') as f:
                scripts_data = json.load(f)
        except FileNotFoundError:
            scripts_data = []

        # cerco lo script con lo screen_id
        for script in scripts_data:
            if script["screen_id"] == screen_id:
                # se trovo il match, aggiorno il titolo
                script["titolo"] = titolo

                # aggiorno il file json
                with open(json_file, 'w') as f:
                    json.dump(scripts_data, f, indent=4)

                return

        print(f"Screen_id {screen_id} non trovato.")

    def deleteScriptId(screen_id):
        json_file = "../../scripts.json"
        try:
            with open(json_file, 'r') as f:
                scripts_data = json.load(f)
        except FileNotFoundError:
            scripts_data = []

        for script in scripts_data:
            if script["screen_id"] == screen_id:
                # se trovo il match, elimino lo script
                scripts_data.remove(script)

                # aggiorno il file json
                with open(json_file, 'w') as f:
                    json.dump(scripts_data, f, indent=4)

                print(f"Script eliminato per screen_id {screen_id}")
                return

        print(f"Screen_id {screen_id} non trovato.")

class TelegramRequestManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, json_file: str = "active_requests.json"):
        if not hasattr(self, 'initialized'):
            self.json_file = json_file
            self.initialized = True
            self.on_response_callback = None

    def create_request(self, type: str) -> str:
        request_data = {
            "type": type,
            "response": None,
            "timestamp": time.time()
        }

        with open(self.json_file, "w") as f:
            json.dump(request_data, f)

        return "Ok"

    def save_response(self, message_text: str) -> bool:
        try:
            # Carica il file JSON
            with open(self.json_file, "r") as f:
                data = json.load(f)

            # Controlla se esiste la chiave 'type' e se la risposta è presente
            if "type" in data and "response" in data:
                data["response"] = message_text  # Aggiorna la risposta

                with open(self.json_file, "w") as f:
                    json.dump(data, f, indent=4)

                return True
            else:
                return False

        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f" save_response - errore: {e}")
            return False

    def get_response(self) -> Optional[str]:
        try:
            with open(self.json_file, "r") as f:
                data = json.load(f)

                # Verifica se esiste la chiave "response"
                if "response" in data:
                    response = data["response"]  # Ottieni la risposta direttamente

                    if response is not None and self.on_response_callback:
                        self.on_response_callback(response)

                    return response

        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"get_response - errore: {e}")
        return None

    def clear_file(self) -> bool:
        try:
            with open(self.json_file, "w") as f:
                json.dump({}, f)
            print(f"File {self.json_file} è stato svuotato con successo.")
            return True

        except Exception as e:
            print(f" clear_file - errore: {e}")
            return False

# Funzione per caricare variabili da un file .env
def load_env(file_path="../../.env"):
    if os.path.exists(file_path):
        with open(file_path) as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value

# Carica le variabili
load_env()


class TelegramBot:
    _instance = None
    _config_file = "../../bot_config.json"

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            # Prova a caricare la configurazione e inizializzare il bot
            if os.path.exists(cls._config_file):
                with open(cls._config_file, "r") as f:
                    config = json.load(f)

                # Assicura che authorized_user_id venga trattato come una lista
                authorized_users = config.get('authorized_user_id', [])
                if isinstance(authorized_users, str):
                    authorized_users = [int(uid) for uid in authorized_users.split(",") if uid.strip().isdigit()]

                cls._instance = cls.init_bot(config['token'], authorized_users)
                #cls._instance = cls.init_bot(config['token'], config['authorized_user_id'])

            else:
                raise Exception("Bot non ancora inizializzato. Chiamare prima init_bot() con token e authorized_user_id")
        return cls._instance

    @classmethod
    def init_bot(cls, token, authorized_user_id):
        if cls._instance is None:
            cls._instance = cls(token, authorized_user_id)
            # Salva la configurazione
            config = {"token": token, "authorized_user_id": authorized_user_id}
            with open(cls._config_file, "w") as f:
                json.dump(config, f)
        return cls._instance

    def __init__(self, token, authorized_users):

        def monitor_scripts():
            while True:
                try:
                    with open("../../scripts.json", "r") as f:
                        scripts_data = json.load(f)
                except (FileNotFoundError, json.JSONDecodeError):
                    scripts_data = []

                current_time = time.time()

                # Crea una nuova lista senza gli script che sono scaduti o le screen che non esistono
                scripts_data_to_save = []

                for script in scripts_data:
                    screen_exists = False
                    try:
                        existing_screens = subprocess.check_output(
                            ["screen", "-list"]
                        ).decode("utf-8")
                        if script["screen_id"] in existing_screens:
                            screen_exists = True
                    except subprocess.CalledProcessError:
                        pass  # Se il comando fallisce, significa che non ci sono screen attivi.

                    if screen_exists:
                        if (
                            "titolo" not in script
                            and script["status"] == "running"
                            and (current_time - script["start_time"]) > 600
                        ):
                            # Prova a terminare la sessione screen
                            try:
                                subprocess.check_output(
                                    ["screen", "-S", script["screen_id"], "-X", "quit"]
                                )
                                print(
                                    f" La sessione screen con ID {script['screen_id']} è stata fermata automaticamente."
                                )
                            except subprocess.CalledProcessError:
                                print(
                                    f" Impossibile fermare la sessione screen con ID {script['screen_id']}."
                                )
                            print(
                                f" Lo script con ID {script['screen_id']} ha superato i 10 minuti e verrà rimosso."
                            )
                        else:
                            scripts_data_to_save.append(script)
                    else:
                        print(
                            f" La sessione screen con ID {script['screen_id']} non esiste più e verrà rimossa."
                        )

                # Salva la lista aggiornata, senza gli script scaduti o le screen non esistenti
                with open("../../scripts.json", "w") as f:
                    json.dump(scripts_data_to_save, f, indent=4)

                time.sleep(60)  # Controlla ogni minuto

        # Avvia il thread di monitoraggio
        monitor_thread = threading.Thread(target=monitor_scripts, daemon=True)
        monitor_thread.start()

        if TelegramBot._instance is not None:
            raise Exception(
                "Questa classe è un singleton! Usa get_instance() per ottenere l'istanza."
            )

        self.token = token
        self.authorized_users = authorized_users
        self.chat_id = authorized_users
        self.bot = telebot.TeleBot(token)
        self.request_manager = TelegramRequestManager()

        # Registra gli handler
        self.register_handlers()

    def register_handlers(self):

        """@self.bot.message_handler(commands=['start'])
        def start(message):
            self.handle_start(message)"""

        @self.bot.message_handler(commands=["get_id"])
        def get_id(message):
            self.handle_get_id(message)

        @self.bot.message_handler(commands=["start"])
        def start_script(message):
            self.handle_start_script(message)

        @self.bot.message_handler(commands=["list"])
        def list_scripts(message):
            self.handle_list_scripts(message)

        @self.bot.message_handler(commands=["stop"])
        def stop_script(message):
            self.handle_stop_script(message)

        @self.bot.message_handler(commands=["screen"])
        def screen_status(message):
            self.handle_screen_status(message)

        @self.bot.message_handler(func=lambda message: True)
        def handle_all_messages(message):
            self.handle_response(message)

    def is_authorized(self, user_id):
        return user_id in self.authorized_users

    def handle_get_id(self, message):
        if not self.is_authorized(message.from_user.id):
            print(" Non sei autorizzato.")
            self.bot.send_message(message.chat.id, " Non sei autorizzato.")
            return

        print(f"Il tuo ID utente è: `{message.from_user.id}`")
        self.bot.send_message(
            message.chat.id,
            f"Il tuo ID utente è: `{message.from_user.id}`",
            parse_mode="Markdown",
        )

    def handle_start_script(self, message):
        if not self.is_authorized(message.from_user.id):
            print(f" Non sei autorizzato. {message.from_user.id}")
            self.bot.send_message(message.chat.id, " Non sei autorizzato.")
            return

        screen_id = str(uuid.uuid4())[:8]
        debug_mode = os.getenv("DEBUG")

        if debug_mode == "True":
            subprocess.Popen(["python3", "../../test_run.py", screen_id])
        else:
            # Verifica se lo screen con il nome esiste già
            try:
                subprocess.check_output(["screen", "-list"])
                existing_screens = subprocess.check_output(["screen", "-list"]).decode(
                    "utf-8"
                )
                if screen_id in existing_screens:
                    print(f" Lo script con ID {screen_id} è già in esecuzione.")
                    self.bot.send_message(
                        message.chat.id,
                        f" Lo script con ID {screen_id} è già in esecuzione.",
                    )
                    return
            except subprocess.CalledProcessError:
                pass  # Se il comando fallisce, significa che non ci sono screen attivi.

            # Crea la sessione screen e avvia lo script al suo interno
            command = [
                "screen",
                "-dmS",
                screen_id,
                "python3",
                "../../test_run.py",
                screen_id,
            ]

            # Avvia il comando tramite subprocess
            subprocess.Popen(command)

        # Creazione oggetto script info
        script_info = {
            "screen_id": screen_id,
            "start_time": time.time(),
            "status": "running",
            "user_id": message.from_user.id,
        }

        # Salvataggio nel file JSON
        json_file = "../../scripts.json"

        # Carica i dati esistenti o crea una nuova lista
        try:
            with open(json_file, "r") as f:
                scripts_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            scripts_data = []

        # Aggiungi il nuovo script
        scripts_data.append(script_info)

        # Scrivi il file aggiornato
        with open(json_file, "w") as f:
            json.dump(scripts_data, f, indent=4)

    def handle_list_scripts(self, message):
        if not self.is_authorized(message.from_user.id):
            print(" Non sei autorizzato.")
            self.bot.send_message(message.chat.id, " Non sei autorizzato.")
            return

        try:
            with open("../../scripts.json", "r") as f:
                scripts_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            scripts_data = []

        if not scripts_data:
            print(" Nessuno script registrato.")
            self.bot.send_message(message.chat.id, " Nessuno script registrato.")
            return

        current_time = time.time()
        msg = [" **Script Registrati:**\n"]

        for script in scripts_data:
            # Calcola la durata
            duration = current_time - script["start_time"]
            if "end_time" in script:
                duration = script["end_time"] - script["start_time"]

            # Formatta la durata
            hours, rem = divmod(duration, 3600)
            minutes, seconds = divmod(rem, 60)
            duration_str = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"

            # Icona stato
            status_icons = {"running": "", "stopped": "", "completed": ""}

            # Costruisci riga
            line = (
                f"• ID: `{script['screen_id']}`\n"
                f"• Stato: {status_icons.get(script['status'], '')}\n"
                f"• Stop: `/stop {script['screen_id']}`\n"
                f"• Screen: `/screen {script['screen_id']}`\n"
                f"• Durata: {duration_str}\n"
                f"• Download:\n{script.get('titolo', 'N/A')}\n"
            )
            msg.append(line)

        # Formatta la risposta finale
        final_msg = "\n".join(msg)
        if len(final_msg) > 4000:
            final_msg = final_msg[:4000] + "\n[...] (messaggio troncato)"

        print(f"{final_msg}")
        self.bot.send_message(message.chat.id, final_msg, parse_mode="Markdown")

    def handle_stop_script(self, message):
        if not self.is_authorized(message.from_user.id):
            print(" Non sei autorizzato.")
            self.bot.send_message(message.chat.id, " Non sei autorizzato.")
            return

        parts = message.text.split()
        if len(parts) < 2:
            try:
                with open("../../scripts.json", "r") as f:
                    scripts_data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                scripts_data = []

            running_scripts = [s for s in scripts_data if s["status"] == "running"]

            if not running_scripts:
                print(" Nessuno script attivo da fermare.")
                self.bot.send_message(
                    message.chat.id, " Nessuno script attivo da fermare."
                )
                return

            msg = " **Script Attivi:**\n"
            for script in running_scripts:
                msg += f" `/stop {script['screen_id']}` per fermarlo\n"

            print(f"{msg}")
            self.bot.send_message(message.chat.id, msg, parse_mode="Markdown")

        elif len(parts) == 2:
            screen_id = parts[1]

            try:
                with open("../../scripts.json", "r") as f:
                    scripts_data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                scripts_data = []

            # Filtra la lista eliminando lo script con l'ID specificato
            new_scripts_data = [
                script for script in scripts_data if script["screen_id"] != screen_id
            ]

            if len(new_scripts_data) == len(scripts_data):
                # Nessun elemento rimosso, quindi ID non trovato
                print(f" Nessuno script attivo con ID `{screen_id}`.")
                self.bot.send_message(
                    message.chat.id,
                    f" Nessuno script attivo con ID `{screen_id}`.",
                    parse_mode="Markdown",
                )
                return

            # Terminare la sessione screen
            try:
                subprocess.check_output(["screen", "-S", screen_id, "-X", "quit"])
                print(f" La sessione screen con ID {screen_id} è stata fermata.")
            except subprocess.CalledProcessError:
                print(
                    f" Impossibile fermare la sessione screen con ID `{screen_id}`."
                )
                self.bot.send_message(
                    message.chat.id,
                    f" Impossibile fermare la sessione screen con ID `{screen_id}`.",
                    parse_mode="Markdown",
                )
                return

            # Salva la lista aggiornata senza lo script eliminato
            with open("../../scripts.json", "w") as f:
                json.dump(new_scripts_data, f, indent=4)

            print(f" Script `{screen_id}` terminato con successo!")
            self.bot.send_message(
                message.chat.id,
                f" Script `{screen_id}` terminato con successo!",
                parse_mode="Markdown",
            )

    def handle_response(self, message):
        text = message.text
        if self.request_manager.save_response(text):
            print(f" Risposta salvata correttamente per il tipo {text}")
        else:
            print(" Nessuna richiesta attiva.")
            self.bot.reply_to(message, " Nessuna richiesta attiva.")

    def handle_screen_status(self, message):
        command_parts = message.text.split()
        if len(command_parts) < 2:
            print(" ID mancante nel comando. Usa: /screen <ID>")
            self.bot.send_message(
                message.chat.id, " ID mancante nel comando. Usa: /screen <ID>"
            )
            return

        screen_id = command_parts[1]
        temp_file = f"/tmp/screen_output_{screen_id}.txt"

        try:
            # Verifica se lo screen con l'ID specificato esiste
            existing_screens = subprocess.check_output(["screen", "-list"]).decode('utf-8')
            if screen_id not in existing_screens:
                print(f" La sessione screen con ID {screen_id} non esiste.")
                self.bot.send_message(message.chat.id, f" La sessione screen con ID {screen_id} non esiste.")
                return

            # Cattura l'output della screen
            subprocess.run(
                ["screen", "-X", "-S", screen_id, "hardcopy", "-h", temp_file],
                check=True,
            )
        except subprocess.CalledProcessError as e:
            print(f" Errore durante la cattura dell'output della screen: {e}")
            self.bot.send_message(
                message.chat.id,
                f" Errore durante la cattura dell'output della screen: {e}",
            )
            return

        if not os.path.exists(temp_file):
            print(" Impossibile catturare l'output della screen.")
            self.bot.send_message(
                message.chat.id, " Impossibile catturare l'output della screen."
            )
            return

        try:
            # Leggi il file con la codifica corretta
            with open(temp_file, "r", encoding="latin-1") as file:
                screen_output = file.read()

            # Pulisci l'output
            cleaned_output = re.sub(
                r"[\x00-\x1F\x7F]", "", screen_output
            )  # Rimuovi caratteri di controllo
            cleaned_output = cleaned_output.replace(
                "\n\n", "\n"
            )  # Rimuovi newline multipli
                    
            # Inizializza le variabili
            cleaned_output_0 = None  # o ""
            cleaned_output_1 = None  # o ""

            # Dentro cleaned_output c'è una stringa recupero quello che si trova tra ## ##
            download_section = re.search(r"##(.*?)##", cleaned_output, re.DOTALL)
            if download_section:
                cleaned_output_0 = "Download: " + download_section.group(1).strip()

            # Recupero tutto quello che viene dopo con ####
            download_section_bottom = re.search(r"####(.*)", cleaned_output, re.DOTALL)
            if download_section_bottom:
                cleaned_output_1 = download_section_bottom.group(1).strip()

            # Unico i due risultati se esistono
            if cleaned_output_0 and cleaned_output_1:
                cleaned_output = f"{cleaned_output_0}\n{cleaned_output_1}"
                # Rimuovo 'segments.py:302' e 'downloader.py:385' se presente
                cleaned_output = re.sub(r'downloader\.py:\d+', '', cleaned_output)
                cleaned_output = re.sub(r'segments\.py:\d+', '', cleaned_output)

            # Invia l'output pulito
            print(f" Output della screen {screen_id}:\n{cleaned_output}")
            self._send_long_message(
                message.chat.id, f" Output della screen {screen_id}:\n{cleaned_output}"
            )

        except Exception as e:
            print(
                f" Errore durante la lettura o l'invio dell'output della screen: {e}"
            )
            self.bot.send_message(
                message.chat.id,
                f" Errore durante la lettura o l'invio dell'output della screen: {e}",
            )

        # Cancella il file temporaneo
        os.remove(temp_file)

    def send_message(self, message, choices):

        formatted_message = message
        if choices:
            formatted_choices = "\n".join(choices)
            formatted_message = f"{message}\n\n{formatted_choices}"

        for chat_id in self.authorized_users:
            self.bot.send_message(chat_id, formatted_message)

        """ if choices is None:
            if self.chat_id:
                print(f"{message}")
                self.bot.send_message(self.chat_id, message)
        else:
            formatted_choices = "\n".join(choices)
            message = f"{message}\n\n{formatted_choices}"
            if self.chat_id:
                print(f"{message}")
                self.bot.send_message(self.chat_id, message) """

    def _send_long_message(self, chat_id, text, chunk_size=4096):
        """Suddivide e invia un messaggio troppo lungo in più parti."""
        for i in range(0, len(text), chunk_size):
            print(f"{text[i:i+chunk_size]}")
            self.bot.send_message(chat_id, text[i : i + chunk_size])

    def ask(self, type, prompt_message, choices, timeout=60):
        self.request_manager.create_request(type)

        if choices is None:
            print(f"{prompt_message}")
            """ self.bot.send_message(
                self.chat_id,
                f"{prompt_message}",
            ) """
            for chat_id in self.authorized_users:  # Manda a tutti gli ID autorizzati
                self.bot.send_message(chat_id, f"{prompt_message}")
        else:
            print(f"{prompt_message}\n\nOpzioni: {', '.join(choices)}")
            """ self.bot.send_message(
                self.chat_id,
                f"{prompt_message}\n\nOpzioni: {', '.join(choices)}",
            ) """
            for chat_id in self.authorized_users:  # Manda a tutti gli ID autorizzati
                self.bot.send_message(chat_id, f"{prompt_message}\n\nOpzioni: {', '.join(choices)}")

        start_time = time.time()
        while time.time() - start_time < timeout:
            response = self.request_manager.get_response()
            if response is not None:
                return response
            time.sleep(1)

        print(" Timeout: nessuna risposta ricevuta.")
        for chat_id in self.authorized_users:  # Manda a tutti gli ID autorizzati
            self.bot.send_message(chat_id, " Timeout: nessuna risposta ricevuta.")
        self.request_manager.clear_file()
        return None

    def run(self):
        print(" Avvio del bot...")
        with open("../../scripts.json", "w") as f:
            json.dump([], f)
        self.bot.infinity_polling()


def get_bot_instance():
    return TelegramBot.get_instance()

# Esempio di utilizzo
if __name__ == "__main__":

    # Usa le variabili
    token = os.getenv("TOKEN_TELEGRAM")
    authorized_users = os.getenv("AUTHORIZED_USER_ID")

    # Controlla se le variabili sono presenti
    if not token:
        print("Errore: TOKEN_TELEGRAM non è definito nel file .env.")
        sys.exit(1)

    if not authorized_users:
        print("Errore: AUTHORIZED_USER_ID non è definito nel file .env.")
        sys.exit(1)

    try:
        TOKEN = token  # Inserisci il token del tuo bot Telegram sul file .env
        AUTHORIZED_USER_ID = list(map(int, authorized_users.split(",")))  # Inserisci il tuo ID utente Telegram sul file .env
    except ValueError as e:
        print(f"Errore nella conversione degli ID autorizzati: {e}. Controlla il file .env e assicurati che gli ID siano numeri interi separati da virgole.")
        sys.exit(1)

    # Inizializza il bot
    bot = TelegramBot.init_bot(TOKEN, AUTHORIZED_USER_ID)
    bot.run()

"""
start - Avvia lo script
list - Lista script attivi
get - Mostra ID utente Telegram
"""
