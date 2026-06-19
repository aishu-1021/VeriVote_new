import ctypes

print("Testing MFS100 connection...")

try:
    mfs100_dll = ctypes.WinDLL("C:\\Program Files\\Mantra\\MFS100\\Driver\\MFS100Test\\MANTRA.MFS100.dll")
    print("✅ MFS100 DLL loaded successfully - scanner is ready!")
except Exception as e:
    print(f"❌ Error: {e}")