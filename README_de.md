# PCB Things Manager

[中文](README.md) | [English](README_en.md)

> ⚠️ **Haftungsausschluss**:  
> Dieses Projekt befindet sich derzeit noch in der **Entwicklungsphase**. Funktionen können unvollständig sein und Fehler (Bugs) können noch vorhanden sein. Die Nutzung wird nur zu Lernzwecken oder in Nicht-Produktionsumgebungen empfohlen.

**PCB Things Manager** ist ein einfaches, aber leistungsstarkes Bestandsverwaltungssystem auf Basis von Flask, das für Elektronik-Bastler und Ingenieure entwickelt wurde.

**[Änderungsprotokoll (Changelog, nur Chinesisch)](CHANGELOG.md)**

## ✨ Funktionen

*   **📦 Bestandsverwaltung**: Hinzufügen, Bearbeiten und Löschen von Bauteilen. Verfolgen Sie Menge, Gehäusetyp und Lagerort.
*   **💰 Kostenberechnung**: Unterstützung für Mehrwährungsumrechnung (CNY/USD/EUR), automatische Berechnung von Stückpreis und Gesamtwert.
*   **🏷️ Kategorisierung**: Erstellen Sie Haupt- und Unterkategorien zur Organisation.
*   **📄 BOM (Stücklisten) Verwaltung**:
    *   **Drag & Drop** Upload für CSV-Dateien.
    *   Automatischer Abgleich von BOM-Komponenten mit dem Bestand.
    *   Erkennung fehlender Teile und Ein-Klick-Ausbuchung.
*   **🖥️ Modernes UI/UX**:
    *   **Toast-Benachrichtigungen** für direktes Feedback.
    *   **Bearbeiten ohne Neuladen** der Seite.
    *   Einklappbare Seitenleiste mit Speicherfunktion.
    *   Vollständige Integration von FontAwesome-Icons.
*   **📊 Statistik**: Übersicht über den gesamten Bestandswert, Anzahl der Komponenten und Verteilung.
*   **🌍 Mehrsprachigkeit**: **Deutsch**, **Englisch** und **Chinesisch**. Sprache in den Einstellungen änderbar.
*   **🔒 Lokale Bereitstellung**: Alle statischen Assets (wie Icons) werden lokal gehostet. Offline-fähig.

## 🛠️ Installation & Nutzung

### Voraussetzungen

*   Python 3.8 oder höher
*   pip (Python-Paketmanager)

### Schritte

1.  **Repository klonen**

    ```bash
    git clone https://github.com/yourusername/PCB_Things_Manager.git
    cd PCB_Things_Manager
    ```

2.  **Virtuelle Umgebung erstellen (Empfohlen)**

    ```bash
    # Windows
    python -m venv venv
    .\venv\Scripts\activate

    # Linux/macOS
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Abhängigkeiten installieren**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Anwendung starten**

    ```bash
    python app.py
    ```

    Die Anwendung startet unter: `http://127.0.0.1:5000`

## 📂 Projektstruktur

*   `app.py`: Hauptdatei der Flask-Anwendung mit Routen und Logik.
*   `templates/`: HTML-Vorlagendateien (Jinja2).
*   `static/`: Statische Assets (CSS, JS, Schriftarten, Lokalisierungsdateien).
    *   `locales/`: Speichert `en.json`, `zh.json`, `de.json` Übersetzungsdateien.
*   `dataset/`: Datenspeicherverzeichnis.
    *   `inventory.sqlite`: SQLite-Datenbankdatei (wird beim ersten Start automatisch erstellt).
    *   `csv_files/`: Vom Benutzer hochgeladene BOM-CSV-Dateien.

## 📝 Lizenz

Dieses Projekt ist unter der **GPL-3.0** Lizenz lizenziert. Weitere Details finden Sie in der Datei [LICENSE](LICENSE).

---
<i><span style="color: grey">Dieses Projekt wurde mit Unterstützung von KI entwickelt.</span></i>
