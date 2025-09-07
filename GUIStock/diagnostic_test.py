import tkinter as tk

print("🔍 Diagnostic Test for Add Company Function")
print("=" * 50)

try:
    # Test 1: Import
    print("Test 1: Importing add_company...")
    from dbutils.company_utils import add_company
    print("✅ Import successful")

    # Test 2: Check if function exists
    print("Test 2: Checking function...")
    print(f"Function type: {type(add_company)}")
    print("✅ Function exists")

    # Test 3: Create root window
    print("Test 3: Creating root window...")
    root = tk.Tk()
    root.title("Diagnostic Test")
    root.geometry("200x100")
    print("✅ Root window created")

    # Test 4: Try calling add_company with error handling
    print("Test 4: Calling add_company...")
    try:
        add_company(root)
        print("✅ add_company called successfully")
    except Exception as e:
        print(f"❌ Error in add_company: {e}")
        import traceback
        traceback.print_exc()

    print("✅ All tests completed")

except Exception as e:
    print(f"❌ Error during diagnostic: {e}")
    import traceback
    traceback.print_exc()

print("\n🏁 Diagnostic complete - check results above")
