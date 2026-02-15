
import sys
import os

# Mock PySide6
from PySide6.QtWidgets import QApplication

def test_orbital_dynamics_load():
    print("Testing Orbital Dynamics Module Load...")
    try:
        from client.views.orbital_dynamics import OrbitalDynamics
        print("Successfully imported OrbitalDynamics.")
    except ImportError as e:
        print(f"Import Error: {e}")
        return

    try:
        app = QApplication(sys.argv)
        # Mock Vector Client
        widget = OrbitalDynamics(vector_client=None)
        print("Successfully instantiated OrbitalDynamics widget.")
    except Exception as e:
        print(f"Instantiation Error: {e}")

if __name__ == "__main__":
    test_orbital_dynamics_load()
