# Temporary: Disable progressive search for now
def setup_progressive_search(combobox, values_list):
    """Simplified version - just set up basic combobox without progressive search"""

    # Just set the values normally
    combobox['values'] = values_list

    # Only handle ESC key to clear
    def on_escape(event):
        if event.keysym == 'Escape':
            combobox.set('')

    combobox.bind('<KeyPress-Escape>', on_escape)

    # Show all values when clicking in the field
    def on_focus(event):
        combobox['values'] = values_list

    combobox.bind('<FocusIn>', on_focus)
