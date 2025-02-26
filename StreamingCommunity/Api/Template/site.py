# 19.06.24

import sys


# External library
from rich.console import Console


# Variable
console = Console()
available_colors = ['red', 'magenta', 'yellow', 'cyan', 'green', 'blue', 'white']
column_to_hide = ['Slug', 'Sub_ita', 'Last_air_date', 'Seasons_count', 'Url']


def get_select_title(table_show_manager, media_search_manager):
    """
    Display a selection of titles and prompt the user to choose one.

    Returns:
        MediaItem: The selected media item.
    """
    # Determine column_info dynamically for (search site)
    if not media_search_manager.media_list:
        console.print("\n[red]No media items available.")
        return None
    
    # Example of available colors for columns
    available_colors = ['red', 'magenta', 'yellow', 'cyan', 'green', 'blue', 'white']
    
    # Retrieve the keys of the first media item as column headers
    first_media_item = media_search_manager.media_list[0]
    column_info = {"Index": {'color': available_colors[0]}}  # Always include Index with a fixed color

    # Assign colors to the remaining keys dynamically
    color_index = 1
    for key in first_media_item.__dict__.keys():

        if key.capitalize() in column_to_hide:
            continue

        if key in ('id', 'type', 'name', 'score'):  # Custom prioritization of colors
            if key == 'type':
                column_info["Type"] = {'color': 'yellow'}
            elif key == 'name':
                column_info["Name"] = {'color': 'magenta'}
            elif key == 'score':
                column_info["Score"] = {'color': 'cyan'}

        else:
            column_info[key.capitalize()] = {'color': available_colors[color_index % len(available_colors)]}
            color_index += 1

    table_show_manager.add_column(column_info)

    # Populate the table with title information
    for i, media in enumerate(media_search_manager.media_list):
        media_dict = {'Index': str(i)}

        for key in first_media_item.__dict__.keys():
            if key.capitalize() in column_to_hide:
                continue

            # Ensure all values are strings for rich add table
            media_dict[key.capitalize()] = str(getattr(media, key))

        table_show_manager.add_tv_show(media_dict)

    # Run the table and handle user input
    last_command = table_show_manager.run(force_int_input=True, max_int_input=len(media_search_manager.media_list))
    table_show_manager.clear()

    # Handle user's quit command
    if last_command == "q" or last_command == "quit":
        console.print("\n[red]Quit [white]...")
        sys.exit(0)

    # Check if the selected index is within range
    if 0 <= int(last_command) < len(media_search_manager.media_list):
        return media_search_manager.get(int(last_command))
    
    else:
        console.print("\n[red]Wrong index")
        sys.exit(0)
