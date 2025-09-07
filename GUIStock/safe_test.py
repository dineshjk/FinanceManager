import tkinter as tk
import sys

def safe_test():
    """Safe test that won't get stuck"""
    print("🧪 Safe Test for Enhanced Add Company Window")
    print("=" * 50)

    try:
        # Test import first
        from dbutils.company_utils import add_company
        print("✅ Successfully imported add_company")

        # Create a simple test button window
        root = tk.Tk()
        root.title("Safe Test - Click to Test Add Company")
        root.geometry("400x200")
        root.configure(bg="#f0f8ff")

        # Add instructions
        label = tk.Label(root, text="Click the button below to test\nthe enhanced add company window",
                        font=("Helvetica", 12), bg="#f0f8ff")
        label.pack(pady=20)

        # Test button
        def test_add_company():
            try:
                add_company(root)
                print("✅ Add company window opened successfully")
            except Exception as e:
                print(f"❌ Error opening add company: {e}")
                import traceback
                traceback.print_exc()

        test_btn = tk.Button(root, text="🏢 Test Add Company Window",
                            command=test_add_company,
                            font=("Helvetica", 14, "bold"),
                            bg="#32cd32", fg="white",
                            padx=20, pady=10)
        test_btn.pack(pady=10)

        # Exit button
        exit_btn = tk.Button(root, text="❌ Exit Test",
                            command=root.quit,  # Use quit instead of destroy
                            font=("Helvetica", 12),
                            bg="#dc143c", fg="white",
                            padx=15, pady=5)
        exit_btn.pack(pady=10)

        print("✅ Safe test window created")
        print("👆 Use the buttons in the window to test")

        # Start the GUI
        root.mainloop()
        root.destroy()  # Clean up

    except Exception as e:
        print(f"❌ Error during safe test: {e}")
        import traceback
        traceback.print_exc()

    print("✅ Safe test completed")

if __name__ == "__main__":
    safe_test()
