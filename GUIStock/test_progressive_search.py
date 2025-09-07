import tkinter as tk
from tkinter import ttk

def test_progressive_search():
    """Test progressive search functionality in isolation"""
    root = tk.Tk()
    root.title("Progressive Search Test")
    root.geometry("400x300")

    # Test data
    sectors = ["Banking", "IT", "Pharma", "Auto", "FMCG", "Energy", "Metals",
               "Telecom", "Media", "Realty", "Capital Goods", "Consumer Durables"]

    # Instructions
    tk.Label(root, text="Test Progressive Search", font=("Helvetica", 16, "bold")).pack(pady=10)
    tk.Label(root, text="Type in the dropdown below to filter options").pack(pady=5)

    # Create combobox with progressive search
    sector_var = tk.StringVar()
    sector_combo = ttk.Combobox(root, textvariable=sector_var, width=30,
                               font=("Helvetica", 12), values=sectors)
    sector_combo.pack(pady=20)

    # Simple progressive search implementation
    def on_text_change(*args):
        """Filter combobox values based on current text"""
        try:
            current_text = sector_var.get().strip()
            print(f"Text changed to: '{current_text}'")  # Debug output

            if not current_text:
                sector_combo['values'] = sectors
                print("Showing all sectors")
            else:
                filtered = [s for s in sectors if s.lower().startswith(current_text.lower())]
                sector_combo['values'] = filtered
                print(f"Filtered to: {filtered}")

        except Exception as e:
            print(f"Error in filtering: {e}")
            sector_combo['values'] = sectors

    # Bind to StringVar
    sector_var.trace_add('write', on_text_change)

    # ESC to clear
    def on_escape(event):
        if event.keysym == 'Escape':
            sector_var.set('')
            sector_combo['values'] = sectors

    sector_combo.bind('<KeyPress-Escape>', on_escape)

    # Instructions
    tk.Label(root, text="Instructions:", font=("Helvetica", 12, "bold")).pack(pady=(20, 5))
    tk.Label(root, text="• Type 'b' to see Banking\n• Type 'it' to see IT\n• Type 'auto' to see Auto\n• Press ESC to clear").pack()

    # Debug output area
    tk.Label(root, text="Check terminal for debug output", font=("Helvetica", 10, "italic")).pack(pady=10)

    # Exit button
    tk.Button(root, text="Exit", command=root.destroy,
             font=("Helvetica", 12), bg="#dc143c", fg="white").pack(pady=10)

    print("Progressive search test started - check the GUI window")
    root.mainloop()

if __name__ == "__main__":
    test_progressive_search()
