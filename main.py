import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtGui import QFontDatabase, QFont
from client.views.logic_gate import LogicGate

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Vector Infinity")
        self.resize(1600, 900) # Set a larger default size

        # Set LogicGate as the central widget
        self.logic_gate = LogicGate()
        self.setCentralWidget(self.logic_gate)

        # Handle signals (e.g. switching scenes)
        self.logic_gate.request_dashboard.connect(self.on_dashboard_requested)

    def on_dashboard_requested(self):
        print("Dashboard requested! (Future implementation)")

# --- VECTOR CORE INTEGRATION ---
import qasync
import asyncio
from client.api.vector_client import VectorClient

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Debugging: Catch silent crashes
    def exception_hook(exctype, value, traceback):
        # 1. Graceful shutdown on critical error or interrupt
        try:
            if 'logic_gate' in globals():
                globals()['logic_gate'].shutdown()
        except:
            pass

        # 2. Quiet exit for User Interrupts
        if issubclass(exctype, (KeyboardInterrupt, SystemExit)):
             print("\n[VECTOR] USER TERMINATION DETECTED. CLEAN EXIT.")
             sys.exit(0)
             
        # 3. Log real critical errors
        with open("crash_log.txt", "w") as f:
            import traceback as tb
            f.write(f"CRITICAL ERROR: {value}\n")
            tb.print_exception(exctype, value, traceback, file=f)
        print(f"CRITICAL ERROR: {value}")
        sys.__excepthook__(exctype, value, traceback)
        sys.exit(1)
    sys.excepthook = exception_hook
    
    # FIREWALL: Set a robust default font before anything else
    app.setFont(QFont("Segoe UI", 10))

    # LOAD CUSTOM FONTS
    font_id = QFontDatabase.addApplicationFont("assets/fonts/JetBrainsMono-Bold.ttf")
    if font_id != -1:
        font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
        app_font = QFont(font_family, 10)
        app.setFont(app_font)

    # [HEAVY INDUSTRY] Upgrade to Async Event Loop
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    # Initialize The Brain (Vector Client)
    vector_client = VectorClient()
    
    # Initialize UI (The Logic Gate)
    # The MainWindow class is no longer needed as LogicGate will be the main window
    # and will be initialized directly with the vector_client.
    logic_gate = LogicGate(vector_client) # Pass client to UI
    logic_gate.show()
    
    # Graceful Shutdown
    app.aboutToQuit.connect(logic_gate.shutdown)
    
    # Start the Engine
    # Start the Engine
    with loop:
        loop.run_forever()
