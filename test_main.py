import sys
import pytest
from PySide6.QtWidgets import QApplication
from main import MainWindow

@pytest.fixture
def app(qtbot):
    """Fixture to handle QApplication creation."""
    test_app = QApplication.instance()
    if test_app is None:
        test_app = QApplication(sys.argv)
    return test_app

def test_window_title(qtbot):
    """Test that the main window has the correct title."""
    window = MainWindow()
    qtbot.addWidget(window)
    assert window.windowTitle() == "PySide6 Classic App"

def test_window_geometry(qtbot):
    """Test that the window geometry is set correctly."""
    window = MainWindow()
    qtbot.addWidget(window)
    # Check if width and height are as expected
    assert window.width() == 800
    assert window.height() == 600
