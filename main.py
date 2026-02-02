import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtGui import QFontDatabase
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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # LOAD FONTS
    QFontDatabase.addApplicationFont("assets/fonts/JetBrainsMono-Bold.ttf")
    
    window = MainWindow()
    window.show()
    
    # Graceful Shutdown
    app.aboutToQuit.connect(window.logic_gate.shutdown)
    
    sys.exit(app.exec())
