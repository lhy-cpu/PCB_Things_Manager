# PCB Things Manager

[中文](README.md) | [Deutsch](README_de.md)

> ⚠️ **Disclaimer**:  
> This project is currently in **Deep Development**. Features may be incomplete, and bugs may exist. Recommended for educational use or non-production environments only. Please backup data regularly.

**PCB Things Manager** is a simple yet powerful inventory management system built with Flask, designed for electronics hobbyists and engineers to manage PCB components, modules, and Bills of Materials (BOM).

**[CHANGELOG (Chinese Only)](CHANGELOG.md)**

## ✨ Features

*   **📦 Inventory Management**: Add, edit, and delete components. Track quantity, package type, and location.
*   **💰 Cost Calculation**: Supports multi-currency (CNY/USD/EUR) exchange rates, automatic unit price and total value calculation.
*   **🏷️ Categorization**: Create custom primary and secondary categories to organize your library.
*   **📄 BOM (Bill of Materials) Management**:
    *   **Smart Matching**: Customize special matching rules to improve component identification.
    *   **Rules Management**: New special rules management page, supporting JSON rules CRUD, Import/Export.
    *   **Drag & Drop** upload for CSV/BOM files.
    *   Automatically match BOM components with existing inventory.
    *   Quickly identify missing parts and one-click stock deduction.
*   **🖥️ Modern UI/UX**:
    *   **Toast Notifications** for instant feedback.
    *   **Edit in Place** without page refresh.
    *   **Fixed Sidebar**: Stays fixed while scrolling, collapsible with user preference memory.
    *   Fully integrated with FontAwesome icons.
    *   **UTC Time Support**: Backend unified UTC storage, Frontend automatic local time conversion.
*   **📊 Statistics Dashboard**: Overview of total inventory value, component count, and category distribution.
*   **🌍 Multi-language**: Built-in support for **English**, **Chinese (Simplified)**, and **German**. Switch language in Settings.
*   **🔒 Local Deployment**: All static assets hosted locally. No CDN dependencies, fully offline capable.

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
    *   `special_rules.json`: Stores special matching rules.
    *   `csv_files/`: User-uploaded BOM CSV files.

## 📝 License

This project is licensed under the **GPL-3.0** License. See the [LICENSE](LICENSE) file for details.

---
<i><span style="color: grey">This project was developed with the assistance of AI.</span></i>
