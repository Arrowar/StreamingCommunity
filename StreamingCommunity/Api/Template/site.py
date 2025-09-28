# 19.06.24

# External library
from rich.console import Console


# Internal utilities
from StreamingCommunity.Api.Template.config_loader import site_constant
from StreamingCommunity.TelegramHelp.telegram_bot import get_bot_instance


# Variable
console = Console()
available_colors = ['red', 'magenta', 'yellow', 'cyan', 'green', 'blue', 'white']
column_to_hide = ['Slug', 'Sub_ita', 'Last_air_date', 'Seasons_count', 'Url', 'Image', 'Path_id']


def get_select_title(table_show_manager, media_search_manager, num_results_available): 
    """
    Display a selection of titles and prompt the user to choose one.
    Handles both console and Telegram bot input.

    Parameters:
        table_show_manager: Manager for console table display.
        media_search_manager: Manager holding the list of media items.
        num_results_available (int): The number of media items available for selection.

    Returns:
        MediaItem: The selected media item, or None if no selection is made or an error occurs.
    """
    if not media_search_manager.media_list:
        
        # console.print("\n[red]No media items available.")
        return None

    if site_constant.TELEGRAM_BOT:
        bot = get_bot_instance()
        prompt_message = f"Inserisci il numero del titolo che vuoi selezionare (da 0 a {num_results_available - 1}):"
        
        user_input_str = bot.ask(
            "select_title_from_list_number",
            prompt_message,
            None
        )

        if user_input_str is None: 
            bot.send_message("Timeout: nessuna selezione ricevuta.", None)
            return None

        try:
            chosen_index = int(user_input_str)
            if 0 <= chosen_index < num_results_available:
                selected_item = media_search_manager.get(chosen_index)
                if selected_item:
                    return selected_item
                    
                else:
                    bot.send_message(f"Errore interno: Impossibile recuperare il titolo con indice {chosen_index}.", None)
                    return None
            else:
                bot.send_message(f"Selezione '{chosen_index}' non valida. Inserisci un numero compreso tra 0 e {num_results_available - 1}.", None)
                return None
                
        except ValueError:
            bot.send_message(f"Input '{user_input_str}' non valido. Devi inserire un numero.", None)
            return None
            
        except Exception as e:
            bot.send_message(f"Si è verificato un errore durante la selezione: {e}", None)
            return None

    else:
        
        # Logica originale per la console
        if not media_search_manager.media_list:
            console.print("\n[red]No media items available.")
            return None
        
        first_media_item = media_search_manager.media_list[0]
        column_info = {"Index": {'color': available_colors[0]}}

        color_index = 1
        for key in first_media_item.__dict__.keys():

            if key.capitalize() in column_to_hide:
                continue

            if key in ('id', 'type', 'name', 'score'):
                if key == 'type': 
                    column_info["Type"] = {'color': 'yellow'}

                elif key == 'name': 
                    column_info["Name"] = {'color': 'magenta'}
                elif key == 'score': 
                    column_info["Score"] = {'color': 'cyan'}
                    
            else:
                column_info[key.capitalize()] = {'color': available_colors[color_index % len(available_colors)]}
                color_index += 1

        table_show_manager.clear() 
        table_show_manager.add_column(column_info)

        for i, media in enumerate(media_search_manager.media_list):
            media_dict = {'Index': str(i)}
            for key in first_media_item.__dict__.keys():
                if key.capitalize() in column_to_hide:
                    continue
                media_dict[key.capitalize()] = str(getattr(media, key))
            table_show_manager.add_tv_show(media_dict)

        last_command_str = table_show_manager.run(force_int_input=True, max_int_input=len(media_search_manager.media_list))
        table_show_manager.clear()

        if last_command_str is None or last_command_str.lower() in ["q", "quit"]: 
            console.print("\n[red]Selezione annullata o uscita.")
            return None 

        try:
           
            selected_index = int(last_command_str)
            
            if 0 <= selected_index < len(media_search_manager.media_list):
                return media_search_manager.get(selected_index)
                
            else:
                console.print("\n[red]Indice errato o non valido.")
                return None
                
        except ValueError:
            console.print("\n[red]Input non numerico ricevuto dalla tabella.")
            return None