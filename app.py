import os
import sqlite3
import csv
import io
import json
import re
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, g, session, jsonify
from werkzeug.utils import secure_filename
from datetime import datetime, timezone

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['UPLOAD_FOLDER'] = os.path.join('dataset', 'csv_files')
app.config['DATABASE'] = os.path.join('dataset', 'inventory.sqlite')
app.config['LOCALES_FOLDER'] = os.path.join('static', 'locales')

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.dirname(app.config['DATABASE']), exist_ok=True)
os.makedirs(app.config['LOCALES_FOLDER'], exist_ok=True)

# --- i18n support ---
def load_locale(lang_code):
    try:
        path = os.path.join(app.config['LOCALES_FOLDER'], f'{lang_code}.json')
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

@app.template_filter('pretty_json')
def pretty_json(value):
    return json.dumps(value, ensure_ascii=False, indent=2)

@app.before_request
def before_request():
    g.lang = session.get('lang', 'zh') # Default to Chinese
    g.translations = load_locale(g.lang)

def get_currency_config(lang_code):
    """
    Returns currency configuration for the given language.
    """
    db = get_db()
    
    # Defaults
    config = {'code': 'CNY', 'symbol': '¥', 'rate': 1.0}
    
    # Map language to currency code
    lang_map = {
        'zh': 'CNY',
        'en': 'USD',
        'de': 'EUR'
    }
    
    target_currency = lang_map.get(lang_code, 'CNY')
    
    if target_currency == 'CNY':
        return config # Base currency
        
    rate_key = f'rate_{target_currency}'
    
    # Defaults fallback map
    defaults = {
        'rate_USD': 0.14,
        'rate_EUR': 0.13
    }
    
    # Ensure settings table exists and has defaults before querying
    try:
        row = db.execute('SELECT value FROM settings WHERE key = ?', (rate_key,)).fetchone()
    except sqlite3.OperationalError:
        # If table wrong, return config with default rate if known, else 1.0
        # Actually simplest to just return default config but with correct rate if possible
        config['rate'] = defaults.get(rate_key, 1.0)
        return config

    if row:
        try:
            rate = float(row['value'])
        except (ValueError, TypeError):
            rate = 1.0
    else:
        # Key missing in DB, use default
        rate = defaults.get(rate_key, 1.0)
    
    symbols = {
        'CNY': '¥',
        'USD': '$',
        'EUR': '€'
    }
    
    return {
        'code': target_currency,
        'symbol': symbols.get(target_currency, '?'),
        'rate': rate
    }

def convert_to_base(amount, lang_code):
    """
    Converts amount from the currency associated with lang_code to base currency (CNY).
    Algorithm: Base = Amount / Rate
    Example: 14 USD / 0.14 = 100 CNY
    """
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return 0.0
        
    config = get_currency_config(lang_code)
    try:
         return amount / config['rate']
    except ZeroDivisionError:
         return amount

def convert_from_base(amount, lang_code):
    """
    Converts amount from base currency (CNY) to the currency associated with lang_code.
    Algorithm: Local = Base * Rate
    Example: 100 CNY * 0.14 = 14 USD
    """
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return 0.0

    config = get_currency_config(lang_code)
    return amount * config['rate']

def get_trans(key, default=None):
    return g.translations.get(key, default or key)

@app.context_processor
def inject_i18n():
    def get_text(key, default=None):
        return g.translations.get(key, default or key)
    
    # helper for templates to start currency conversion
    def format_price(amount_base):
        try:
            val = convert_from_base(amount_base, g.lang)
            return "{:.5f}".format(val)
        except:
             return "0.00000"

    # We need to access DB for currency config, which might not be ready during initial setup
    # So we wrap it in a try-except or check
    try:
        currency_config = get_currency_config(g.lang)
        symbol = currency_config['symbol']
    except:
        symbol = '¥'

    return dict(_=get_text, current_lang=g.lang, currency_symbol=symbol, format_price=format_price)

@app.route('/set_language/<lang_code>')
def set_language(lang_code):
    session['lang'] = lang_code
    return redirect(request.referrer or url_for('index'))
# --------------------

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(app.config['DATABASE'])
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        # Components table
        db.execute('''
            CREATE TABLE IF NOT EXISTS components (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model TEXT NOT NULL,
                footprint TEXT,
                primary_category TEXT,
                secondary_category TEXT,
                supplier_part TEXT,
                current_quantity INTEGER DEFAULT 0,
                remark TEXT,
                unit_price REAL DEFAULT 0.0
            )
        ''')
        # Transaction history
        db.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                component_id INTEGER,
                change_amount INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                note TEXT,
                bom_file_id INTEGER,
                FOREIGN KEY (component_id) REFERENCES components (id)
            )
        ''')
        # BOM Files management
        db.execute('''
            CREATE TABLE IF NOT EXISTS bom_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                display_name TEXT NOT NULL,
                upload_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_matched REAL DEFAULT 0
            )
        ''')
        try:
             db.execute('ALTER TABLE bom_files ADD COLUMN last_matched REAL DEFAULT 0')
        except:
             pass
        # BOM Rows/Matches (stores the state of a BOM file's rows and their matching status)
        db.execute('''
            CREATE TABLE IF NOT EXISTS bom_matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bom_file_id INTEGER,
                row_index INTEGER,
                csv_data TEXT, -- JSON or separator-delimited string of original row data
                matched_component_id INTEGER, -- NULL if unmatched
                quantity_needed INTEGER,
                designator TEXT,
                status TEXT DEFAULT 'pending', -- pending, saved, committed
                transaction_id INTEGER, -- Link to the transaction if committed
                FOREIGN KEY (bom_file_id) REFERENCES bom_files (id),
                FOREIGN KEY (matched_component_id) REFERENCES components (id)
            )
        ''')
        
        # Categories Management
        db.execute('''
            CREATE TABLE IF NOT EXISTS category_primary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS category_secondary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                primary_id INTEGER,
                FOREIGN KEY (primary_id) REFERENCES category_primary (id),
                UNIQUE(name, primary_id)
            )
        ''')
        
        # Settings
        db.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        # Seed default rates
        db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('rate_USD', '0.14')")
        db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('rate_EUR', '0.13')")
        
        # Migration: Sync existing categories from components table to category tables
        # This ensures we have data even if tables were just created
        existing_comps = db.execute('SELECT DISTINCT primary_category, secondary_category FROM components').fetchall()
        for row in existing_comps:
            p_name = row['primary_category']
            s_name = row['secondary_category']
            
            if p_name:
                # Insert Primary
                try:
                    db.execute('INSERT OR IGNORE INTO category_primary (name) VALUES (?)', (p_name,))
                except: pass
                
                # Get Primary ID
                pid_row = db.execute('SELECT id FROM category_primary WHERE name = ?', (p_name,)).fetchone()
                if pid_row and s_name:
                    # Insert Secondary
                    try:
                       db.execute('INSERT OR IGNORE INTO category_secondary (name, primary_id) VALUES (?, ?)', (s_name, pid_row['id']))
                    except: pass
                    
        db.commit()

# Initialize DB on first run
if not os.path.exists(app.config['DATABASE']):
    init_db()
else:
    # Check if tables exist, if not, create them (quick fix for dev)
    init_db()

def _get_category_tree(db):
    """
    Returns a dict { 'primary_name': [list of secondary_names] }
    """
    primaries = db.execute('SELECT * FROM category_primary ORDER BY name').fetchall()
    tree = {}
    for p in primaries:
        seconds = db.execute('SELECT name FROM category_secondary WHERE primary_id = ? ORDER BY name', (p['id'],)).fetchall()
        tree[p['name']] = [s['name'] for s in seconds]
    return tree

# --- Matching Logic Helpers ---
def load_special_rules():
    try:
        path = os.path.join('dataset', 'special_rules.json')
        if os.path.exists(path):
            mtime = os.path.getmtime(path)
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f), mtime
    except:
        pass
    return [], 0

def save_special_rules(rules):
    try:
        path = os.path.join('dataset', 'special_rules.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(rules, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving rules: {e}")
        return False

def normalize_name(name):
    if not name: return ""
    # "SMF 3.3A" -> "SMF3.3A", remove spaces/dashes/underscores, uppercase
    return str(name).replace(" ", "").replace("-", "").replace("_", "").upper()

def normalize_footprint(fp):
    if not fp: return ""
    fp = str(fp).upper().strip()
    
    # Priority: Extract standard imperial code if present anywhere in string
    # E.g. "LED0603-RD" -> "0603", "R0603" -> "0603", "C0402" -> "0402"
    valid_imperial = ['01005', '0201', '0402', '0603', '0805', '1206', '1210', '2010', '2512']
    # Regex search for these codes surrounded by non-digits
    pattern = r'(?<!\d)(' + '|'.join(valid_imperial) + r')(?!\d)'
    
    match = re.search(pattern, fp)
    if match:
        return match.group(1)
            
    # Fallback: Remove verbose suffixes starting with _
    # SOD-123_L2.8... -> SOD-123
    if '_' in fp:
        fp = fp.split('_')[0]
    
    # Handle "SOD-123" vs "SOD123"
    fp = fp.replace("-", "")
    
    return fp

def find_best_match(row_data, all_components, special_rules):
    # 1. Special Rules Check
    target_match_criteria = {}
    
    # Alias mapping for rules (Rule Key -> CSV Header Key)
    # This helps when rules use 'model' but CSV has 'Comment'
    key_aliases = {
        'model': 'Comment',
        'footprint': 'Footprint',
        'supplier_part': 'Supplier Part'
    }
    
    for rule in special_rules:
        criteria = rule.get('criteria', {})
        target = rule.get('target', {})
        if not criteria: continue
        
        use_smart = rule.get('use_smart_detect', False)
        
        match_count = 0
        total_criteria = len(criteria)
        
        for key, val in criteria.items():
            # Resolve key from alias if needed
            row_key = key
            if row_key not in row_data and row_key in key_aliases:
                row_key = key_aliases[row_key]
                
            row_val_raw = str(row_data.get(row_key, ''))
            
            # Comparison Helper
            def check_val(r_val, c_val):
                if not use_smart:
                    return r_val.strip() == str(c_val).strip()
                else:
                    # Smart Detect
                    # Use footprint normalizer if key implies footprint
                    if 'footprint' in key.lower():
                        return normalize_footprint(r_val) == normalize_footprint(c_val)
                    else:
                        return normalize_name(r_val) == normalize_name(c_val)

            is_match = False
            if isinstance(val, list):
                # OR logic: if row_val matches ANY item in list
                for v in val:
                    if check_val(row_val_raw, v):
                        is_match = True
                        break
            else:
                # Simple string equality check
                if check_val(row_val_raw, val):
                    is_match = True
            
            if is_match:
                match_count += 1
        
        if match_count == total_criteria:
            # Rule applies!
            if 'model' in target: target_match_criteria['model'] = target['model']
            if 'footprint' in target: target_match_criteria['footprint'] = target['footprint']
            if 'supplier_part' in target: target_match_criteria['supplier_part'] = target['supplier_part']
            break
            
    # Prepare search terms
    search_model_raw = target_match_criteria.get('model', row_data.get('Comment', ''))
    search_footprint_raw = target_match_criteria.get('footprint', row_data.get('Footprint', ''))
    search_supplier_raw = target_match_criteria.get('supplier_part', row_data.get('Supplier Part', ''))

    # 2. Supplier Part Match (Strongest - Exact Match)
    if search_supplier_raw:
        for c in all_components:
            if c['supplier_part'] and c['supplier_part'].strip() == search_supplier_raw.strip():
                return c['id']
                
    # 3. Smart Model + Footprint Match
    bom_model_norm = normalize_name(search_model_raw)
    bom_fp_norm = normalize_footprint(search_footprint_raw)
    
    if not bom_model_norm:
        return None

    best_candidate = None
    
    for c in all_components:
        c_model_norm = c['_n_model']
        c_fp_norm = c['_n_fp']
        
        # Name Match Logic
        name_match = (bom_model_norm == c_model_norm)
        
        # Fuzzy Name: one contains other or starts with
        if not name_match:
             if len(bom_model_norm) > 1 and len(c_model_norm) > 1:
                 # Check if one is prefix of other
                 if bom_model_norm.startswith(c_model_norm) or c_model_norm.startswith(bom_model_norm):
                     name_match = True
        
        if name_match:
            # Check Footprint
            # If footprints match exactly (normalized)
            if bom_fp_norm and c_fp_norm:
                if bom_fp_norm == c_fp_norm:
                    return c['id'] # Good Match
            elif not bom_fp_norm and not c_fp_norm:
                # Neither has footprint, name matches
                best_candidate = c['id']
            elif not bom_fp_norm and c_fp_norm:
                 # BOM has no footprint, component does. Potential match.
                 if best_candidate is None: best_candidate = c['id']
            # If BOM has footprint but Comp doesn't? Or mismatch? Skip.
            
    return best_candidate

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/categories', methods=['GET', 'POST'])
def categories():
    db = get_db()
    
    if request.method == 'POST':
        if 'add_primary' in request.form:
            name = request.form['name'].strip()
            if name:
                try:
                    db.execute('INSERT INTO category_primary (name) VALUES (?)', (name,))
                    db.commit()
                    flash(f'Primary category "{name}" added.')
                except sqlite3.IntegrityError:
                    flash(f'Category "{name}" already exists.', 'error')
        elif 'add_secondary' in request.form:
            p_id = request.form['primary_id']
            name = request.form['name'].strip()
            if name and p_id:
                try:
                    db.execute('INSERT INTO category_secondary (name, primary_id) VALUES (?, ?)', (name, p_id))
                    db.commit()
                    flash(f'Secondary category "{name}" added.')
                except sqlite3.IntegrityError:
                     flash(f'Secondary category "{name}" already exists for this primary.', 'error')
        elif 'delete_primary' in request.form:
            p_id = request.form['id']
            # Delete secondaries first
            db.execute('DELETE FROM category_secondary WHERE primary_id = ?', (p_id,))
            db.execute('DELETE FROM category_primary WHERE id = ?', (p_id,))
            db.commit()
            flash(get_trans('flash_cat_deleted', 'Primary category deleted.'))
        elif 'delete_secondary' in request.form:
            s_id = request.form['id']
            db.execute('DELETE FROM category_secondary WHERE id = ?', (s_id,))
            db.commit()
            flash(get_trans('flash_cat_deleted', 'Secondary category deleted.'))
        
        return redirect(url_for('categories'))

    # Load All
    cats = db.execute('''
        SELECT p.id as pid, p.name as pname, s.id as sid, s.name as sname
        FROM category_primary p
        LEFT JOIN category_secondary s ON p.id = s.primary_id
        ORDER BY p.name, s.name
    ''').fetchall()
    
    # Process into structured object for template
    structure = {}
    for row in cats:
        pid = row['pid']
        if pid not in structure:
            structure[pid] = {'id': pid, 'name': row['pname'], 'children': []}
        if row['sid']:
            structure[pid]['children'].append({'id': row['sid'], 'name': row['sname']})
            
    return render_template('categories.html', categories=structure.values())

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    db = get_db()
    if request.method == 'POST':
        # Update rates
        rate_usd = request.form.get('rate_USD')
        rate_eur = request.form.get('rate_EUR')
        
        if rate_usd:
             db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('rate_USD', ?)", (rate_usd,))
        if rate_eur:
             db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('rate_EUR', ?)", (rate_eur,))
        
        db.commit()
        flash(get_trans('flash_settings_saved', 'Settings saved.'))
        return redirect(url_for('settings'))

    # Load current rates
    rates = {}
    rows = db.execute('SELECT key, value FROM settings').fetchall()
    for r in rows:
        try:
            rates[r['key']] = float(r['value'])
        except (ValueError, TypeError):
            rates[r['key']] = 0.0
    
    # Ensure defaults in view if DB is empty/fresh
    if 'rate_USD' not in rates: rates['rate_USD'] = 0.14
    if 'rate_EUR' not in rates: rates['rate_EUR'] = 0.13

    return render_template('settings.html', rates=rates)

@app.route('/rules', methods=['GET', 'POST'])
def rules():
    rules_data, _ = load_special_rules()

    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            new_rule = json.loads(request.form.get('rule_data'))
            rules_data.append(new_rule)
            save_special_rules(rules_data)
            flash(get_trans('flash_rule_added', 'Rule added.'))
            
        elif action == 'edit':
            index = int(request.form.get('index'))
            new_rule = json.loads(request.form.get('rule_data'))
            if 0 <= index < len(rules_data):
                rules_data[index] = new_rule
                save_special_rules(rules_data)
                flash(get_trans('flash_rule_updated', 'Rule updated.'))
                
        elif action == 'delete':
            index = int(request.form.get('index'))
            if 0 <= index < len(rules_data):
                del rules_data[index]
                save_special_rules(rules_data)
                flash(get_trans('flash_rule_deleted', 'Rule deleted.'))
        
        elif action == 'import':
            file = request.files.get('file')
            mode = request.form.get('mode', 'merge') # 'merge' or 'overwrite'
            
            if file and file.filename.endswith('.json'):
                try:
                    imported_rules = json.load(file)
                    if not isinstance(imported_rules, list):
                        flash(get_trans('flash_invalid_json', 'Invalid JSON format: Root must be a list.'), 'error')
                    else:
                        if mode == 'overwrite':
                            rules_data = imported_rules
                            msg = get_trans('flash_rules_overwritten', 'Rules overwritten.')
                        else:
                            # Merge: Add only if not exactly present
                            added_count = 0
                            # Simple deep equality check
                            current_set = [json.dumps(r, sort_keys=True) for r in rules_data]
                            for r in imported_rules:
                                r_str = json.dumps(r, sort_keys=True)
                                if r_str not in current_set:
                                    rules_data.append(r)
                                    added_count += 1
                            msg = get_trans('flash_rules_merged', f'merged {added_count} rules.').format(added_count)
                        
                        save_special_rules(rules_data)
                        flash(msg)
                except Exception as e:
                    flash(f"Error: {e}", 'error')
            else:
                 flash(get_trans('flash_invalid_file', 'Invalid file.'), 'error')

        return redirect(url_for('rules'))

    return render_template('rules.html', rules=rules_data)

@app.route('/api/rules/export')
def export_rules():
    path = os.path.join('dataset', 'special_rules.json')
    if os.path.exists(path):
        return send_from_directory('dataset', 'special_rules.json', as_attachment=True, download_name='special_rules.json')
    return jsonify([])


@app.route('/inventory', methods=['GET', 'POST'])
def inventory():
    db = get_db()
    if request.method == 'POST':
        if 'add' in request.form:
            model = request.form['model']
            footprint = request.form['footprint']
            
            # --- Category Handling ---
            # Use Manual inputs if filled, else use Selects
            p_cat = request.form.get('primary_category_manual', '').strip()
            if not p_cat:
                p_cat = request.form.get('primary_category_select', '')
            
            s_cat = request.form.get('secondary_category_manual', '').strip()
            if not s_cat:
                s_cat = request.form.get('secondary_category_select', '')

            # --- Auto-Add Category to Dictionary Table if New ---
            if p_cat:
                # Check/Add Primary
                pid = db.execute('SELECT id FROM category_primary WHERE name = ?', (p_cat,)).fetchone()
                if not pid:
                    cur = db.execute('INSERT INTO category_primary (name) VALUES (?)', (p_cat,))
                    pid = cur.lastrowid
                else:
                    pid = pid['id']
                
                if s_cat:
                    # Check/Add Secondary under this primary
                    sid = db.execute('SELECT id FROM category_secondary WHERE name = ? AND primary_id = ?', (s_cat, pid)).fetchone()
                    if not sid:
                        db.execute('INSERT INTO category_secondary (name, primary_id) VALUES (?, ?)', (s_cat, pid))
            # ---------------------------

            supplier = request.form['supplier_part']
            qty = int(request.form['quantity'])
            remark = request.form.get('remark', '')
            
            raw_price = float(request.form.get('unit_price', 0.0))
            # Convert input price (in current currency) to Base Currency (CNY) for storage
            price_base = convert_to_base(raw_price, g.lang)

            cursor = db.execute('''
                INSERT INTO components (model, footprint, primary_category, secondary_category, supplier_part, current_quantity, remark, unit_price)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (model, footprint, p_cat, s_cat, supplier, qty, remark, price_base))
            
            # Initial stock log
            if qty != 0:
                db.execute('INSERT INTO transactions (component_id, change_amount, note) VALUES (?, ?, ?)',
                           (cursor.lastrowid, qty, 'Initial Stock'))
            db.commit()
            flash(get_trans('flash_comp_added', 'Component added successfully!'))
            
        elif 'delete' in request.form:
            comp_id = request.form['component_id']
            db.execute('DELETE FROM components WHERE id = ?', (comp_id,))
            db.execute('DELETE FROM transactions WHERE component_id = ?', (comp_id,))
            db.commit()
            flash(get_trans('flash_comp_deleted', 'Component deleted!'))

        elif 'update_stock' in request.form:
            comp_id = request.form['component_id']
            change = int(request.form['change_amount'])
            note = request.form['note']
            
            db.execute('UPDATE components SET current_quantity = current_quantity + ? WHERE id = ?', (change, comp_id))
            db.execute('INSERT INTO transactions (component_id, change_amount, note) VALUES (?, ?, ?)',
                       (comp_id, change, note))
            db.commit()
            flash(get_trans('flash_stock_updated', 'Stock updated!'))
        
        elif 'edit' in request.form:
            comp_id = request.form['component_id']
            model = request.form['model']
            footprint = request.form['footprint']
            # Re-use category parsing logic or simplify? The edit form will likely have the same complex select/manual
            # For simplicity in this step, let's assume the user edits basic fields or categories via simplified dropdowns
            # But correct logic is needed.
            # Category update:
            p_cat = request.form.get('primary_category_manual', '').strip()
            if not p_cat:
                p_cat = request.form.get('primary_category_select', '')
            
            s_cat = request.form.get('secondary_category_manual', '').strip()
            if not s_cat:
                s_cat = request.form.get('secondary_category_select', '')

            # Add new categories if needed
            if p_cat:
                pid = db.execute('SELECT id FROM category_primary WHERE name = ?', (p_cat,)).fetchone()
                if not pid:
                    cur = db.execute('INSERT INTO category_primary (name) VALUES (?)', (p_cat,))
                    pid = cur.lastrowid
                else:
                    pid = pid['id']
                
                if s_cat:
                    sid = db.execute('SELECT id FROM category_secondary WHERE name = ? AND primary_id = ?', (s_cat, pid)).fetchone()
                    if not sid:
                        db.execute('INSERT INTO category_secondary (name, primary_id) VALUES (?, ?)', (s_cat, pid))
            
            supplier = request.form['supplier_part']
            remark = request.form.get('remark', '')
            
            raw_price = float(request.form.get('unit_price', 0.0))
            price_base = convert_to_base(raw_price, g.lang)

            db.execute('''
                UPDATE components
                SET model=?, footprint=?, primary_category=?, secondary_category=?, supplier_part=?, remark=?, unit_price=?
                WHERE id=?
            ''', (model, footprint, p_cat, s_cat, supplier, remark, price_base, comp_id))
            db.commit()

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                updated_comp = db.execute('SELECT * FROM components WHERE id = ?', (comp_id,)).fetchone()
                return jsonify({
                    'status': 'success',
                    'id': updated_comp['id'],
                    'model': updated_comp['model'],
                    'footprint': updated_comp['footprint'] or '',
                    'primary_category': updated_comp['primary_category'] or '',
                    'secondary_category': updated_comp['secondary_category'] or '',
                    'supplier_part': updated_comp['supplier_part'] or '',
                    'remark': updated_comp['remark'] or '',
                    'unit_price': "{:.5f}".format(convert_from_base(updated_comp['unit_price'], g.lang)),
                    'message': get_trans('flash_comp_updated', 'Component updated successfully!')
                })

            flash(get_trans('flash_comp_updated', 'Component updated successfully!'))

        return redirect(url_for('inventory'))

    components = db.execute('SELECT * FROM components').fetchall()
    
    # Load Category Tree for Dropdowns
    cats = db.execute('''
        SELECT p.name as pname, s.name as sname 
        FROM category_primary p 
        LEFT JOIN category_secondary s ON p.id = s.primary_id
        ORDER BY p.name, s.name
    ''').fetchall()
    
    cat_tree = {}
    for r in cats:
        p = r['pname']
        if p not in cat_tree: cat_tree[p] = []
        if r['sname']: cat_tree[p].append(r['sname'])
        
    return render_template('inventory.html', components=components, cat_tree=cat_tree)

@app.route('/csv_manage', methods=['GET', 'POST'])
def csv_manage():
    db = get_db()
    
    # Sync filesystem with DB
    existing_files = {f['filename'] for f in db.execute('SELECT filename FROM bom_files').fetchall()}
    fs_files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if f.endswith('.csv')]
    
    for fs_file in fs_files:
        if fs_file not in existing_files:
            db.execute('INSERT INTO bom_files (filename, display_name) VALUES (?, ?)', (fs_file, fs_file))
            db.commit()
    
    if request.method == 'POST':
        if 'upload' in request.files:
            file = request.files['upload']
            if file and file.filename.endswith('.csv'):
                filename = secure_filename(file.filename)
                
                # Handle duplicate filenames by appending timestamp
                if os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
                    name, ext = os.path.splitext(filename)
                    filename = f"{name}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}{ext}"
                
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                
                db.execute('INSERT INTO bom_files (filename, display_name) VALUES (?, ?)', 
                           (filename, filename))
                db.commit()
                flash(get_trans('flash_file_uploaded', 'File uploaded successfully!'))

        elif 'rename' in request.form:
            file_id = request.form['file_id']
            new_name = request.form['new_name']
            db.execute('UPDATE bom_files SET display_name = ? WHERE id = ?', (new_name, file_id))
            db.commit()
            flash(get_trans('flash_renamed', 'Renamed successfully!'))
        
        elif 'delete' in request.form:
            file_id = request.form['file_id']
            # Get filename first to delete physical file
            file_record = db.execute('SELECT filename FROM bom_files WHERE id = ?', (file_id,)).fetchone()
            if file_record:
                # Delete matches first
                db.execute('DELETE FROM bom_matches WHERE bom_file_id = ?', (file_id,))
                # Delete file record
                db.execute('DELETE FROM bom_files WHERE id = ?', (file_id,))
                db.commit()
                
                # Delete physical file
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], file_record['filename'])
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                    except OSError:
                        pass # Ignore if file not found or locked
                
                flash(get_trans('flash_file_deleted', 'File deleted successfully!'))
        
        return redirect(url_for('csv_manage'))

    files = db.execute('SELECT * FROM bom_files').fetchall()
    return render_template('csv_manage.html', files=files)

def run_smart_match(db, file_id, special_rules, rules_mtime):
    # Load Components for matching
    all_comps_raw = db.execute('SELECT id, model, footprint, supplier_part FROM components').fetchall()
    all_comps_smart = []
    
    for c in all_comps_raw:
        all_comps_smart.append({
            'id': c['id'], 
            'model': c['model'], 
            'footprint': c['footprint'], 
            'supplier_part': c['supplier_part'],
            '_n_model': normalize_name(c['model']),
            '_n_fp': normalize_footprint(c['footprint'])
        })
        
    # Get all matches that are NOT committed
    matches = db.execute('SELECT * FROM bom_matches WHERE bom_file_id = ? AND status != ?', (file_id, 'committed')).fetchall()
    
    updated_count = 0
    import json
    for m in matches:
        row_data = json.loads(m['csv_data'])
        matched_id = find_best_match(row_data, all_comps_smart, special_rules)
        
        # If we found a match and it is different, update it
        # Note: If user manually set it, this might overwrite. 
        # But 'automatic' implies keeping it in sync.
        # Ideally we only update if it was NOT manually set?
        # But we don't track matches vs manual well. Status 'pending' or 'saved'.
        # Let's assume 'saved' means user looked at it. 'pending' means raw from csv.
        # But user wants rules applied. So we apply.
        
        if matched_id != m['matched_component_id']:
             db.execute('UPDATE bom_matches SET matched_component_id = ? WHERE id = ?', (matched_id, m['id']))
             if matched_id: updated_count += 1
            
    # Update BOM File last matched time
    db.execute('UPDATE bom_files SET last_matched = ? WHERE id = ?', (rules_mtime, file_id))
    db.commit()
    return updated_count

@app.route('/bom_match/<int:file_id>', methods=['GET', 'POST'])
def bom_match(file_id):
    db = get_db()
    bom_file = db.execute('SELECT * FROM bom_files WHERE id = ?', (file_id,)).fetchone()
    
    # Check for rules update on GET
    special_rules, rules_mtime = load_special_rules()
    
    if request.method == 'GET':
        # Safely get last_matched
        last_matched = 0
        if bom_file and 'last_matched' in bom_file.keys():
            last_matched = bom_file['last_matched'] or 0

        # If rules file is newer than last match, run update
        if rules_mtime > last_matched:
            count = run_smart_match(db, file_id, special_rules, rules_mtime)
            if count > 0:
                flash(get_trans('flash_rules_updated', f'Rules updated: {count} matches refreshed.'), 'info')
            else:
                 # Just update timestamp so we don't check again
                 db.execute('UPDATE bom_files SET last_matched = ? WHERE id = ?', (rules_mtime, file_id))
                 db.commit()
        # Reload bom_file if updated
        bom_file = db.execute('SELECT * FROM bom_files WHERE id = ?', (file_id,)).fetchone()
    
    if request.method == 'POST':
        if 'rematch' in request.form:
             count = run_smart_match(db, file_id, special_rules, rules_mtime)
             flash(get_trans('flash_rematch_done', f'Rematched items.'))
             return redirect(url_for('bom_match', file_id=file_id))
        
        # Handle Save or Checkout
        row_indices = request.form.getlist('row_index')
        
        # Iterate over submitted form data
        for i in row_indices:
            # Get data for this row
            matched_comp_id = request.form.get(f'match_{i}') # Can be empty string if 'Manual Select' is default
            qty_needed = int(request.form.get(f'qty_{i}', 0))
            match_id = request.form.get(f'match_row_id_{i}') # ID in bom_matches table if exists
            
            # Logic: Update bom_matches table
            # If committing (Checkout), also do transactions
            pass # We will fill this logic in a moment
            
        if 'save' in request.form:
             # Just update bom_matches
            _save_bom_matches(db, file_id, request.form)
            flash(get_trans('flash_progress_saved', 'Progress saved.'))
        elif 'checkout' in request.form:
            _checkout_bom(db, file_id, request.form)
            flash(get_trans('flash_bom_checkout', 'BOM Checked out and inventory updated.'))
        elif 'reset' in request.form:
            db.execute('DELETE FROM bom_matches WHERE bom_file_id = ?', (file_id,))
            db.commit()
            matches = [] # Force reload
            flash(get_trans('flash_matches_reset', 'Matches reset. Re-parsing CSV...'))
            
        return redirect(url_for('bom_match', file_id=file_id))

    # Load existing matches or parse CSV if not exists
    matches = db.execute('SELECT * FROM bom_matches WHERE bom_file_id = ? ORDER BY row_index', (file_id,)).fetchall()
    
    rows_data = [] # List of dicts to render
    
    if not matches:
        # First time opening or reset, parse CSV
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], bom_file['filename'])
        try:
            # Detect encoding and delimiter
            encodings = ['utf-8-sig', 'gbk', 'utf-16']
            content = ""
            encoding = 'utf-8-sig'
            
            # Simple encoding guess
            for enc in encodings:
                try:
                    with open(filepath, 'r', encoding=enc) as f:
                        content = f.read(4096) # Read a chunk
                        f.seek(0)
                    encoding = enc
                    break
                except:
                    continue
            
            # Detect delimiter from Header
            delimiter = ','
            with open(filepath, 'r', encoding=encoding) as f:
                header_line = f.readline()
                if '\t' in header_line:
                    delimiter = '\t'
                elif ';' in header_line: # Possible regional CSV
                    if header_line.count(';') > header_line.count(','):
                        delimiter = ';'
            
            # Load Smart Match Data
            special_rules, _ = load_special_rules()
            all_comps_raw = db.execute('SELECT id, model, footprint, supplier_part FROM components').fetchall()
            all_comps_smart = []
            for c in all_comps_raw:
                all_comps_smart.append({
                    'id': c['id'], 
                    'model': c['model'], 
                    'footprint': c['footprint'], 
                    'supplier_part': c['supplier_part'],
                    '_n_model': normalize_name(c['model']),
                    '_n_fp': normalize_footprint(c['footprint'])
                })
            
            with open(filepath, 'r', encoding=encoding) as f:
                reader = csv.DictReader(f, delimiter=delimiter)
                
                # Normalize keys (strip whitespace) safely
                if reader.fieldnames:
                    reader.fieldnames = [name.strip() for name in reader.fieldnames]
                
                for idx, row in enumerate(reader):
                    row_data = {
                        'idx': idx,
                        'Quantity': row.get('Quantity', '0').strip(),
                        'Comment': row.get('Comment', '').strip(),
                        'Designator': row.get('Designator', '').strip(),
                        'Footprint': row.get('Footprint', '').strip(),
                        'Supplier Part': row.get('Supplier Part', '').strip(),
                        'Primary Category': row.get('Primary Category', '').strip(),
                        'Secondary Category': row.get('Secondary Category', '').strip(),
                    }
                    
                    # Smart Matching Logic
                    matched_id = find_best_match(row_data, all_comps_smart, special_rules)

                    # Save this initial match to DB
                    # We store the raw CSV row data as JSON-like string for display in future
                    import json
                    db.execute('''
                        INSERT INTO bom_matches (bom_file_id, row_index, csv_data, matched_component_id, quantity_needed, designator, status)
                        VALUES (?, ?, ?, ?, ?, ?, 'pending')
                    ''', (file_id, idx, json.dumps(row_data), matched_id, row_data['Quantity'], row_data['Designator']))
                    
                    rows_data.append({
                        'match_id': None, # New
                        'row_data': row_data,
                        'matched_comp_id': matched_id,
                        'status': 'pending'
                    })
                db.commit()
                # Reload matches
                matches = db.execute('SELECT * FROM bom_matches WHERE bom_file_id = ? ORDER BY row_index', (file_id,)).fetchall()
        except Exception as e:
            flash(f'Error reading CSV: {e}')
            return redirect(url_for('csv_manage'))

    # Load Components for dropdown with Available quantity context
    all_components = db.execute('''
        SELECT 
            c.id, c.model, c.footprint, c.current_quantity, c.unit_price,
            (SELECT COALESCE(SUM(quantity_needed), 0) FROM bom_matches WHERE matched_component_id = c.id AND status = 'saved') as reserved
        FROM components c
    ''').fetchall()
    
    # Prepare data for template
    display_rows = []
    import json
    for m in matches:
        data = json.loads(m['csv_data'])
        display_rows.append({
            'db_id': m['id'],
            'csv_data': data,
            'matched_component_id': m['matched_component_id'],
            'quantity_needed': m['quantity_needed'],
            'status': m['status']
        })

    return render_template('bom_match.html', file=bom_file, rows=display_rows, components=all_components)

def _save_bom_matches(db, file_id, form_data):
    row_indices = form_data.getlist('row_index')
    for i in row_indices:
        match_db_id = form_data.get(f'match_row_id_{i}')
        matched_comp_id = form_data.get(f'match_{i}')
        qty = form_data.get(f'qty_{i}')
        
        if not matched_comp_id or matched_comp_id == 'None':
            matched_comp_id = None
            
        db.execute('''
            UPDATE bom_matches 
            SET matched_component_id = ?, 
                quantity_needed = ?,
                status = CASE WHEN status = 'committed' THEN 'committed' ELSE 'saved' END
            WHERE id = ?
        ''', (matched_comp_id, qty, match_db_id))
    db.commit()

def _checkout_bom(db, file_id, form_data):
    # First, revert any previous committed transactions for these rows
    # Check if we have existing transactions linked to matches
    existing_matches = db.execute('SELECT id, transaction_id, matched_component_id FROM bom_matches WHERE bom_file_id = ?', (file_id,)).fetchall()
    
    for m in existing_matches:
        if m['transaction_id']:
            # Revert transaction: Find it, get amount, add back to component
            trx = db.execute('SELECT change_amount, component_id FROM transactions WHERE id = ?', (m['transaction_id'],)).fetchone()
            if trx:
                # Add back the amount (since checkout subtracts, we add positive of absolute value, or simpler: just reverse the sign of change_amount)
                # change_amount was negative for checkout. We subtract it ( - (-5) = +5 )
                db.execute('UPDATE components SET current_quantity = current_quantity - ? WHERE id = ?', (trx['change_amount'], trx['component_id']))
                db.execute('DELETE FROM transactions WHERE id = ?', (m['transaction_id'],))
    
    # Now process new/current form data
    row_indices = form_data.getlist('row_index')
    filename = db.execute('SELECT filename FROM bom_files WHERE id = ?', (file_id,)).fetchone()['filename']
    
    for i in row_indices:
        match_db_id = form_data.get(f'match_row_id_{i}')
        matched_comp_id = form_data.get(f'match_{i}')
        qty_needed = int(form_data.get(f'qty_{i}', 0))
        
        # Valid match?
        if matched_comp_id and matched_comp_id != 'None':
            # Deduct stock
            db.execute('UPDATE components SET current_quantity = current_quantity - ? WHERE id = ?', (qty_needed, matched_comp_id))
            
            # Create Transaction
            cursor = db.execute('''
                INSERT INTO transactions (component_id, change_amount, note, bom_file_id)
                VALUES (?, ?, ?, ?)
            ''', (matched_comp_id, -qty_needed, f'BOM Match: {filename}', file_id))
            
            trx_id = cursor.lastrowid
            
            # Update match record
            db.execute('''
                UPDATE bom_matches 
                SET matched_component_id = ?, quantity_needed = ?, status = 'committed', transaction_id = ?
                WHERE id = ?
            ''', (matched_comp_id, qty_needed, trx_id, match_db_id))
        else:
            # Update match record (no transaction)
             db.execute('''
                UPDATE bom_matches 
                SET matched_component_id = NULL, quantity_needed = ?, status = 'saved', transaction_id = NULL
                WHERE id = ?
            ''', (qty_needed, match_db_id))

    db.commit()

@app.route('/stats')
def stats():
    db = get_db()
    
    # Updated query to include Reserved quantity from saved matches
    # Available = current_quantity (Physical Stock) - reserved
    # current_quantity already includes previous checkouts (transactions)
    
    stats_data = db.execute('''
        WITH ReservedCounts AS (
            SELECT matched_component_id, SUM(quantity_needed) as reserved_qty
            FROM bom_matches
            WHERE status = 'saved'
            GROUP BY matched_component_id
        ),
        TransactionSums AS (
            SELECT component_id,
                   SUM(CASE WHEN change_amount > 0 THEN change_amount ELSE 0 END) as total_in,
                   SUM(CASE WHEN change_amount < 0 THEN change_amount ELSE 0 END) as total_out
            FROM transactions
            GROUP BY component_id
        )
        SELECT 
            c.id,
            c.model, 
            c.footprint,
            c.current_quantity,
            c.unit_price,
            COALESCE(ts.total_in, 0) as total_in,
            COALESCE(ts.total_out, 0) as total_out,
            COALESCE(rc.reserved_qty, 0) as reserved
        FROM components c
        LEFT JOIN TransactionSums ts ON c.id = ts.component_id
        LEFT JOIN ReservedCounts rc ON c.id = rc.matched_component_id
    ''').fetchall()
    
    # Calculate Total Value.
    # Exclude negative quantities (oversold/excess) from value calculation.
    total_value_base = sum(
        (c['current_quantity'] if c['current_quantity'] > 0 else 0) * (float(c['unit_price'] or 0)) 
        for c in stats_data
    )
    # Used Value = Total Out (always negative, so take abs) * Price
    used_value_base = sum(abs(c['total_out']) * (float(c['unit_price'] or 0)) for c in stats_data)

    # Reserved Value = Reserved Qty * Price (includes excess if reserved exceeds stock, though physically impossible to reserve more than existing usually, but logic allows it)
    reserved_value_base = sum(c['reserved'] * (float(c['unit_price'] or 0)) for c in stats_data)
    
    total_value = convert_from_base(total_value_base, g.lang)
    used_value = convert_from_base(used_value_base, g.lang)
    reserved_value = convert_from_base(reserved_value_base, g.lang)
    
    return render_template('stats.html', stats=stats_data, total_value=total_value, used_value=used_value, reserved_value=reserved_value)

@app.route('/api/component/<int:comp_id>/history')
def component_history(comp_id):
    db = get_db()
    # Join with bom_files to get the name
    transactions = db.execute('''
        SELECT 
            t.change_amount, t.timestamp, t.note, t.bom_file_id, 
            b.display_name as bom_name
        FROM transactions t
        LEFT JOIN bom_files b ON t.bom_file_id = b.id
        WHERE t.component_id = ?
        ORDER BY t.timestamp DESC
    ''', (comp_id,)).fetchall()
    
    data = []
    for t in transactions:
        data.append({
            'amount': t['change_amount'],
            'date': t['timestamp'],
            'note': t['note'],
            'bom_id': t['bom_file_id'],
            'bom_name': t['bom_name']
        })
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)
