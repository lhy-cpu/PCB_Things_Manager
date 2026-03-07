# PCB Things Manager

[中文](README.md) | [English](README_en.md)

> ⚠️ **Haftungsausschluss**:  
> Dieses Projekt befindet sich derzeit noch in der **Entwicklungsphase**. Funktionen können unvollständig sein und Fehler (Bugs) können noch vorhanden sein. Die Nutzung wird nur zu Lernzwecken oder in Nicht-Produktionsumgebungen empfohlen. Bitte sichern Sie Ihre Daten regelmäßig, um Datenverlust zu vermeiden.

**PCB Things Manager** ist ein einfaches, aber leistungsstarkes Bestandsverwaltungssystem auf Basis von Flask, das für Elektronik-Bastler und Ingenieure entwickelt wurde, um PCB-Komponenten, Module und Stücklisten (BOM) zu verwalten.

## ✨ Funktionen

*   **📦 Bestandsverwaltung**: Hinzufügen, Bearbeiten und Löschen von elektronischen Bauteilen. Verfolgen Sie Menge, Gehäusetyp und Lagerort.
*   **🏷️ Kategorisierung**: Erstellen Sie benutzerdefinierte Kategorien, um Ihre Komponentenbibliothek zu organisieren.
*   **📄 BOM (Stücklisten) Verwaltung**:
    *   Hochladen von BOM-Dateien im CSV-Format.
    *   Automatischer Abgleich von Komponenten in der Stückliste mit Ihrem vorhandenen Bestand.
    *   Anzeige fehlender Teile und ausreichender Lagerbestände.
    *   Löschen hochgeladener BOM-Dateien und der zugehörigen Daten.
*   **📊 Statistik-Dashboard**: Übersicht über den gesamten Bestandswert, die Gesamtanzahl der Komponenten und die Verteilung nach Kategorien.
*   **🌍 Mehrsprachigkeit**: Integrierte Unterstützung für **Deutsch**, **Englisch** und **Chinesisch (Vereinfacht)**. Wechseln Sie die Oberflächensprache jederzeit.
*   **🔒 Lokale Bereitstellung**: Alle statischen Assets (wie FontAwesome) werden lokal gehostet. Keine CDN-Abhängigkeiten, vollständig offline-fähig.
*   **📱 Responsives Design**: Fixiertes Seitenleisten-Layout, angepasst für verschiedene Bildschirmgrößen.

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
