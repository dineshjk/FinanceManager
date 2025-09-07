import tkinter as tk
import sys

print("🧪 Testing Enhanced Add Company Window...")
print("=" * 50)

try:
    from dbutils.company_utils import add_company
    print("✅ Successfully imported add_company")

    # Create root window
    root = tk.Tk()
    root.title("Test Root Window")
    root.geometry("300x100")

    # Add a simple button to test
    test_btn = tk.Button(root, text="🏢 Open Add Company Window",
                        command=lambda: add_company(root),
                        font=("Helvetica", 14), bg="#32cd32", fg="white",
                        padx=20, pady=10)
    test_btn.pack(expand=True)

    # Add exit button
    exit_btn = tk.Button(root, text="❌ Exit Test",
                        command=root.destroy,
                        font=("Helvetica", 12), bg="#dc143c", fg="white",
                        padx=15, pady=5)
    exit_btn.pack(pady=10)

    print("✅ Test window created successfully")
    print("👆 Click the button to open the enhanced add company window")

    # Start main loop
    root.mainloop()
    print("✅ Test completed")

except Exception as e:
    print(f"❌ Error during test: {e}")
    import traceback
    traceback.print_exc()
    input("Press Enter to exit...")
