# Vector Infinity 🌌

An advanced astronomical mission assistant integrating **Stellarium** with **AI-driven telemetry**.

## 🚀 Features

*   **Real-time Telemetry**: Connects to Stellarium's Remote Control API.
*   **Vector AI**: Natural language interface for astronomical queries.
*   **Cosmic Inspector**: Multi-object monitoring with dedicated telemetry cards.
*   **Visual/Technical analysis**: Toggle between visual observations (Alt/Az, Rise/Set) and scientific data (Spectral class, TLE, Redshift).

## 🛠️ Prerequisites

1.  **Stellarium**: Installed and running.
    *   Enable the **Remote Control Plugin** in Stellarium (Plugins -> Remote Control -> Load at startup).
    *   Ensure the server is running on `localhost:8090` (default).
2.  **Python 3.10+**

## 📦 Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/YOUR_USERNAME/Vector-Infinity.git
    cd Vector-Infinity
    ```

2.  **Create a Virtual Environment**:
    ```bash
    python -m venv .venv
    # Windows
    .venv\Scripts\activate
    # Linux/Mac
    source .venv/bin/activate
    ```

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## ⚙️ Configuration

The application uses `config.json` for settings.
*   **Stellarium**: Default is `localhost:8090`.
*   **AI Model**: Configure your API keys (e.g., Anthropic, OpenAI) if you plan to use the chat features.
    ```json
    "api_key": "YOUR_KEY_HERE"
    ```

## 🖥️ Running the App

```bash
python main.py
```

## 🤝 Contributing

1.  Fork the Project.
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`).
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`).
4.  Push to the Branch (`git push origin feature/AmazingFeature`).
5.  Open a Pull Request.

---
*Powered by Python & PySide6*
