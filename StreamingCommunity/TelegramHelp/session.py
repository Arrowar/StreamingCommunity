# 04.02.25
# Made by: @GiuPic

import json

session_data = {}

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