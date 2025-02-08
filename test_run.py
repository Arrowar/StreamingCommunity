# 26.11.24

import sys
from StreamingCommunity.run import main
from StreamingCommunity.Util._jsonConfig import config_manager
from StreamingCommunity.TelegramHelp.telegram_bot import TelegramRequestManager, TelegramSession

# Svuoto il file
TELEGRAM_BOT = config_manager.get_bool('DEFAULT', 'telegram_bot')

if TELEGRAM_BOT:
    request_manager = TelegramRequestManager()
    request_manager.clear_file()
    script_id = sys.argv[1] if len(sys.argv) > 1 else "unknown"

    TelegramSession.set_session(script_id)
    main(script_id)
else:
    main()