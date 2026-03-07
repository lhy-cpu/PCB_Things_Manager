# PCB Things Manager

[中文](README.md) | [Deutsch](README_de.md)

> ⚠️ **Disclaimer**:  
> This project is currently in **Deep Development**. Features may be incomplete, and bugs may exist. It is recommended for educational use or non-production environments only. Please ensure you backup your data regularly to avoid data loss.

**PCB Things Manager** is a simple yet powerful inventory management system built with Flask, designed for electronics hobbyists and engineers to manage PCB components, modules, and Bills of Materials (BOM).

## ✨ Features

*   **📦 Inventory Management**: Add, edit, and delete electronic components. Track quantity, package type, and location.
*   **🏷️ Categorization**: Create custom categories to organize your component library.
*   **📄 BOM (Bill of Materials) Management**:
    *   Upload BOM files in CSV format.
    *   Automatically match components in the BOM with your existing inventory.
    *   View missing parts and sufficient stock items.
    *   Delete uploaded BOM files and their associated data.
*   **📊 Statistics Dashboard**: Overview of total inventory value, total component count, and category distribution.
*   **🌍 Multi-language Support**: Built-in support for **English**, **Chinese (Simplified)**, and **German**. Switch interface language on the fly.
*   **🔒 Local Deployment**: All static assets (like FontAwesome) are hosted locally. No CDN dependencies, fully offline capable.
*   **📱 Responsive Design**: Fixed sidebar layout adapted for various screen sizes.

## 🛠️ Installation & Usage

### Prerequisites

*   Python 3.8 or higher
*   pip (Python package manager)

### Steps

1.  **Clone the repository**

    ```bash
    git clone https://github.com/yourusername/PCB_Things_Manager.git
    cd PCB_Things_Manager
    ```

2.  **Create a virtual environment (Recommended)**

    ```bash
    # Windows
    python -m venv venv
    .\venv\Scripts\activate

    # Linux/macOS
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the application**

    ```bash
    python app.py
    ```

     The application will start at: `http://127.0.0.1:5000`

## 📂 Project Structure

*   `app.py`: Main Flask application file containing routes and logic.
*   `templates/`: HTML template files (Jinja2).
*   `static/`: Static assets (CSS, JS, fonts, localization files).
    *   `locales/`: Stores `en.json`, `zh.json`, `de.json` translation files.
*   `dataset/`: Data storage directory.
    *   `inventory.sqlite`: SQLite database file (automatically created on first run).
    *   `csv_files/`: User-uploaded BOM CSV files.

## 📝 License

This project is licensed under the **GPL-3.0** License. See the [LICENSE](LICENSE) file for details.

---
<i><span style="color: grey">This project was developed with the assistance of AI.</span></i>
