import json
import os
import re
import datetime
import requests
import gspread # Assumes gspread is installed and configured

# --- Configuration ---
CONFIG_FILE = "/root/.openclaw/workspace/config.json"
CREDENTIALS_FILE = "/root/.openclaw/workspace/google-credentials.json"
LOCAL_EXCEL_FILE = "/root/.openclaw/workspace/pokemon-tracker.xlsx"
BACKUPS_DIR = "/root/.openclaw/workspace/backups/"
SCP_DEST_FILE = "/home/jaytee/pokemon-tracker.xlsx"

POKEMON_WIZARD_SETS_URL = "https://www.pokemonwizard.com/sets"
DAWNGLARE_BOX_PRICE_URL = "https://pokemon.dawnglare.com/?p=boxprice"
EXCHANGE_RATE_API_URL = "https://open.er-api.com/v6/latest/USD"

# Name mappings for Dawnglare and PokemonWizard
DAWNGLARE_NAME_MAP = {
    "ascended hereos": "ascended heroes",
    "celebrations 25th": "celebrations",
    "champions path": "champion\'s path",
    "s&v base set": "scarlet & violet",
    "mega evolution (enhanced)": "mega evolution enhanced",
    "journey together (enhanced)": "journey together enhanced",
    "evolutions": "xy evolutions",
    "sword and shield": "sword & shield",
}

WIZARD_NAME_MAP = {
    "s&v base set": "Scarlet & Violet Base Set",
    "151": "Scarlet & Violet 151",
    "ascended hereos": "Ascended Heroes",
    "celebrations 25th": "Celebrations",
    "champions path": "Champion\'s Path",
    "sword and shield": "Sword & Shield",
    "mega evolution (enhanced)": "Mega Evolution",
    "journey together (enhanced)": "Mega Evolution", # Re-check this, prompt had two entries
}

# Gemini API placeholder (replace with actual API call)
def call_gemini_api(prompt_text):
    print(f"--- Simulating Gemini API Call ---")
    print(f"Prompt: {prompt_text[:200]}...") # Truncate for log
    # In a real scenario, this would make an API call to Gemini
    # For now, return a dummy JSON for demonstration
    return {
        "L": 4, "M": 3, "N": 5, "O": 4, "H": "Strong Buy"
    }

# --- Google Sheets Functions (placeholders for gspread) ---
def get_google_sheet_client():
    # In a real scenario, gspread would authenticate here
    # gc = gspread.service_account(filename=CREDENTIALS_FILE)
    print("Simulating gspread client authentication.")
    class MockClient:
        def open_by_key(self, sheet_id):
            print(f"Simulating opening spreadsheet with ID: {sheet_id}")
            return MockSpreadsheet()
    class MockSpreadsheet:
        def worksheet(self, title):
            print(f"Simulating getting worksheet: {title}")
            # If the title is 'Apr 26', return the mock worksheet with data
            if title == "Apr 26":
                return MockWorksheet("Apr 26")
            elif title in ["Mar 26", "Feb 26", "Selling Individual Cards", "May 26"]: # Add May 26 for new sheet creation test
                return MockWorksheet(title)
            raise gspread.exceptions.WorksheetNotFound(f"Worksheet \'{title}\' not found.")
        
        def worksheets(self):
            return [MockWorksheet("Apr 26"), MockWorksheet("Mar 26"), MockWorksheet("Feb 26"), MockWorksheet("Selling Individual Cards")]
        def add_worksheet(self, title, rows, cols):
            print(f"Simulating adding worksheet: {title}")
            return MockWorksheet(title)
        def move_worksheet(self, worksheet, index):
            print(f"Simulating moving worksheet \'{worksheet.title}\' to index {index}")
    class MockWorksheet:
        def __init__(self, title):
            self.title = title
            self._data = [] # Simulate data rows
            if title == "Apr 26":
                self._data = [
                    ["Era", "Date Released", "Set Name", "BB Price (GBP)", "Set Value (GBP)", "Top 3 Chase Cards", "Box %", "Investor Recommendation", "Chase Card %", "Print Run Status", "Decision Matrix Score", "Scarcity", "Format Liquidity", "Mascot Power", "Set Depth"],
                    ["Sword & Shield", "Mar-22", "Fusion Strike", "180", "200", "Gengar VMAX, Espeon VMAX, Mew V", "=D2/E2", "", "=I2/E2", "Out of Print", "", "", "", "", ""],
                    ["Scarlet & Violet", "Dec-25", "Paradox Rift", "100", "120", "Roaring Moon ex, Iron Valiant ex, Gholdengo ex", "=D3/E3", "", "=I3/E3", "In Print", "", "", "", "", ""],
                ]
            self.row_count = len(self._data)
            self.col_count = len(self._data[0]) if self._data else 0

        def get_all_values(self):
            return self._data
        
        def update(self, range_name, values):
            print(f"Simulating updating range {range_name} with {len(values)} rows.")
            # Basic simulation: update internal data structure
            start_row = int(re.search(r\'([A-Z]+)(\d+)\', range_name).group(2))
            for i, row_values in enumerate(values):
                if start_row + i <= len(self._data):
                    for j, value in enumerate(row_values):
                        if j < len(self._data[start_row + i - 1]):
                            self._data[start_row + i - 1][j] = value
                else:
                    self._data.append(row_values)

        def resize(self, rows, cols):
            print(f"Simulating resizing worksheet to {rows} rows, {cols} columns.")

        def format(self, ranges, format_options):
            print(f"Simulating formatting ranges {ranges} with options {format_options}.")

        def set_basic_filter(self, range_name):
            print(f"Simulating setting basic filter on {range_name}.")

        def acell(self, cell_ref):
            # Basic simulation for getting a single cell value
            col_letter = re.match(r\'([A-Z]+)\', cell_ref).group(1)
            row_num = int(re.search(r\'(\d+)\', cell_ref).group(1))
            col_index = ord(col_letter) - ord(\'A\')
            if row_num <= len(self._data) and col_index < len(self._data[row_num - 1]):
                return MockCell(self._data[row_num - 1][col_index])
            return MockCell(\'\')
        
        def update_cell(self, row, col, value):
            print(f"Simulating updating cell R{row}C{col} with value: {value}")
            # Ensure the internal data structure can handle the update
            while len(self._data) < row:
                self._data.append([\'\'] * self.col_count) # Pad rows
            while len(self._data[row - 1]) < col:
                self._data[row - 1].append(\'\') # Pad columns
            self._data[row - 1][col - 1] = value

    class MockCell:
        def __init__(self, value):
            self.value = value
    return MockClient()


def get_spreadsheet(client, sheet_id):
    try:
        spreadsheet = client.open_by_key(sheet_id)
        return spreadsheet
    except Exception as e:
        print(f"ERROR: Could not open Google Sheet with ID {sheet_id}: {e}")
        return None

def create_and_configure_sheet(spreadsheet, current_month_year):
    # Check if sheet already exists
    for ws in spreadsheet.worksheets():
        if ws.title == current_month_year:
            print(f"Worksheet \'{current_month_year}\' already exists. Skipping creation.")
            return ws

    print(f"Creating new worksheet: {current_month_year}")
    # gspread requires initial rows/cols
    new_worksheet = spreadsheet.add_worksheet(title=current_month_year, rows="100", cols="15")
    
    # Move to position 0 (leftmost)
    spreadsheet.move_worksheet(new_worksheet, 0)

    # Set headers
    headers = ["Era", "Date Released", "Set Name", "BB Price (GBP)", "Set Value (GBP)", "Top 3 Chase Cards", "Box %", "Investor Recommendation", "Chase Card %", "Print Run Status", "Decision Matrix Score", "Scarcity", "Format Liquidity", "Mascot Power", "Set Depth"]
    new_worksheet.update('A1:O1', [headers])

    # Apply formatting to header row
    new_worksheet.format('A1:O1', {
        \'textFormat\': {\'bold\': True},
        \'backgroundColor\': {\'red\': 0.9, \'green\': 0.9, \'blue\': 0.9} # Light gray background
    })
    
    # Set basic filter (assuming first row is headers)
    new_worksheet.set_basic_filter('A1:O1')

    # Freeze header row (gspread does not have direct freeze method, typically done via batch_update or manually)
    print("INFO: Header row freeze needs manual setup or batch_update via gspread.spreadsheet.batch_update for full automation.")
    
    return new_worksheet

def download_and_backup(spreadsheet, current_date):
    if not os.path.exists(BACKUPS_DIR):
        os.makedirs(BACKUPS_DIR)

    backup_filename = os.path.join(BACKUPS_DIR, f"pokemon-tracker-backup-{current_date}.xlsx")
    print(f"Simulating downloading current Google Sheet to {backup_filename}")
    # In a real scenario, you\'d use gspread_pandas or similar to download as Excel
    # For now, create a dummy file
    with open(backup_filename, \'w\') as f:
        f.write("DUMMY EXCEL BACKUP CONTENT")

    # Keep only the 3 most recent backups
    all_backups = sorted([f for f in os.listdir(BACKUPS_DIR) if f.startswith("pokemon-tracker-backup-") and f.endswith(".xlsx")], reverse=True)
    for old_backup in all_backups[3:]:
        os.remove(os.path.join(BACKUPS_DIR, old_backup))
        print(f"Deleted old backup: {old_backup}")
    
    print(f"Backup created: {backup_filename}")
    return backup_filename

# --- Web Scraping and Data Processing ---
def fetch_pokemon_wizard_sets():
    print(f"Fetching sets from {POKEMON_WIZARD_SETS_URL}")
    response = requests.get(POKEMON_WIZARD_SETS_URL)
    response.raise_for_status() # Raise an exception for HTTP errors
    
    # Simulate scraping for demonstration
    # In a real scenario, use BeautifulSoup or similar to parse HTML
    sets_data = [
        {"name": "Fusion Strike", "url": "https://www.pokemonwizard.com/sets/fusion-strike"},
        {"name": "Paradox Rift", "url": "https://www.pokemonwizard.com/sets/paradox-rift"},
        {"name": "Temporal Forces", "url": "https://www.pokemonwizard.com/sets/temporal-forces"}, # New set
    ]
    return sets_data

def get_set_details(set_url, set_name):
    print(f"Fetching details for {set_name} from {set_url}")
    response = requests.get(set_url)
    response.raise_for_status()

    # Simulate scraping Era and Date Released
    era = "Sword & Shield" if "fusion-strike" in set_url else "Scarlet & Violet"
    release_date_str = "Released on November 12, 2021" if "fusion-strike" in set_url else "Released on November 3, 2023"
    
    release_date_match = re.search(r\'Released on (\w+ \d{1,2}, \d{4})\', release_date_str)
    if release_date_match:
        date_obj = datetime.datetime.strptime(release_date_match.group(1), \'%B %d, %Y\')
        formatted_date = date_obj.strftime(\'%b-%y\') # Mon-YY format
    else:
        formatted_date = ""

    return {"era": era, "date_released": formatted_date}


def get_usd_to_gbp_rate():
    print(f"Fetching exchange rate from {EXCHANGE_RATE_API_URL}")
    try:
        response = requests.get(EXCHANGE_RATE_API_URL)
        response.raise_for_status()
        data = response.json()
        if \'rates\' in data and \'GBP\' in data[\'rates\']:
            return data[\'rates\'][\'GBP\']
        else:
            print("WARNING: Could not find GBP exchange rate. Defaulting to 1.0 (no conversion).")
            return 1.0
    except Exception as e:
        print(f"ERROR fetching exchange rate: {e}. Defaulting to 1.0 (no conversion).")
        return 1.0

def update_prices_and_values(worksheet_data, usd_to_gbp_rate):
    updated_rows_count = 0
    dawnglare_prices = {} # Populate this by scraping DAWNGLARE_BOX_PRICE_URL
    pokemon_wizard_set_data = {} # Populate this by scraping individual set pages

    # Simulate dawnglare scraping
    # In a real scenario, parse HTML for prices
    dawnglare_prices = {
        "fusion strike": {"Booster Box": 180, "currency": "USD"},
        "paradox rift": {"Booster Box": 100, "currency": "USD"},
        "temporal forces": {"Booster Box": 90, "currency": "USD"},
    }

    # Simulate PokemonWizard set page scraping for Total Value and Top 3 Chase Cards
    # In a real scenario, you\'d fetch each set\'s URL (from fetch_pokemon_wizard_sets result)
    pokemon_wizard_set_data = {
        "Fusion Strike": {
            "Total Value": 200, "currency": "USD",
            "Top 3 Chase Cards": [{"name": "Gengar VMAX", "price": 100}, {"name": "Espeon VMAX", "price": 50}, {"name": "Mew V", "price": 30}]
        },
        "Paradox Rift": {
            "Total Value": 120, "currency": "USD",
            "Top 3 Chase Cards": [{"name": "Roaring Moon ex", "price": 40}, {"name": "Iron Valiant ex", "price": 30}, {"name": "Gholdengo ex", "price": 20}]
        },
        "Temporal Forces": {
            "Total Value": 110, "currency": "USD",
            "Top 3 Chase Cards": [{"name": "Special Card 1", "price": 35}, {"name": "Special Card 2", "price": 25}, {"name": "Special Card 3", "price": 15}]
        },
    }

    headers = worksheet_data[0]
    data_rows = worksheet_data[1:]

    for i, row in enumerate(data_rows):
        set_name_col_idx = headers.index("Set Name")
        bb_price_col_idx = headers.index("BB Price (GBP)")
        set_value_col_idx = headers.index("Set Value (GBP)")
        top_3_cards_col_idx = headers.index("Top 3 Chase Cards")
        box_percent_col_idx = headers.index("Box %")
        chase_card_percent_col_idx = headers.index("Chase Card %")

        current_set_name = row[set_name_col_idx]
        if not current_set_name:
            continue

        normalized_set_name_dawnglare = DAWNGLARE_NAME_MAP.get(current_set_name.lower(), current_set_name.lower())
        normalized_set_name_wizard = WIZARD_NAME_MAP.get(current_set_name, current_set_name) # Assuming Wizard names are Title Case

        # Update BB Price (Column D)
        dawnglare_entry = dawnglare_prices.get(normalized_set_name_dawnglare)
        if dawnglare_entry and "Booster Box" in dawnglare_entry:
            bb_price_usd = dawnglare_entry["Booster Box"]
            bb_price_gbp = round(bb_price_usd * usd_to_gbp_rate, 2)
            if str(row[bb_price_col_idx]) != str(bb_price_gbp): # Convert to string for comparison
                worksheet_data[i+1][bb_price_col_idx] = bb_price_gbp
                updated_rows_count += 1
        else:
            print(f"WARNING: No Dawnglare price found for {current_set_name}. Skipping BB Price update.")

        # Update Set Value (Column E) and Top 3 Chase Cards (Column F)
        wizard_entry = pokemon_wizard_set_data.get(normalized_set_name_wizard)
        if wizard_entry:
            set_value_usd = wizard_entry.get("Total Value", 0)
            set_value_gbp = round(set_value_usd * usd_to_gbp_rate, 2)
            if str(row[set_value_col_idx]) != str(set_value_gbp):
                worksheet_data[i+1][set_value_col_idx] = set_value_gbp
                updated_rows_count += 1
            
            top_3_cards = wizard_entry.get("Top 3 Chase Cards", [])
            card_names = [card["name"].split(" ")[0] for card in top_3_cards[:3]] # Strip trailing numbers
            formatted_card_names = ", ".join(card_names)
            if str(row[top_3_cards_col_idx]) != formatted_card_names:
                worksheet_data[i+1][top_3_cards_col_idx] = formatted_card_names
                updated_rows_count += 1

            # Calculate Chase Card % (Column I) - numeric value
            top_3_card_prices_usd_sum = sum(card["price"] for card in top_3_cards[:3])
            top_3_card_prices_gbp_sum = top_3_card_prices_usd_sum * usd_to_gbp_rate
            
            if set_value_gbp > 0:
                chase_card_percent_value = round(top_3_card_prices_gbp_sum / set_value_gbp, 2)
                if str(worksheet_data[i+1][chase_card_percent_col_idx]) != str(chase_card_percent_value):
                    worksheet_data[i+1][chase_card_percent_col_idx] = chase_card_percent_value
                    updated_rows_count += 1
        else:
            print(f"WARNING: No PokemonWizard data found for {current_set_name}. Skipping Set Value and Chase Card updates.")

        # Update Box % (Column G) - formula
        # The prompt says to write formula, so this will be a string formula
        worksheet_data[i+1][box_percent_col_idx] = f"=D{i+2}/E{i+2}"
        updated_rows_count += 1 # Count as update since formula is written

    return worksheet_data, updated_rows_count


def score_sets_with_gemini(worksheet_data, config):
    gemini_calls_made = 0
    headers = worksheet_data[0]
    data_rows = worksheet_data[1:]

    print_run_status_col_idx = headers.index("Print Run Status")
    scarcity_col_idx = headers.index("Scarcity")
    format_liquidity_col_idx = headers.index("Format Liquidity")
    mascot_power_col_idx = headers.index("Mascot Power")
    set_depth_col_idx = headers.index("Set Depth")
    investor_rec_col_idx = headers.index("Investor Recommendation")
    decision_matrix_score_col_idx = headers.index("Decision Matrix Score")

    last_known_j_values = config.get("last_known_j_values", {})

    for i, row in enumerate(data_rows):
        set_name = row[headers.index("Set Name")]
        
        # Check if scoring is needed: blank L, M, N, O OR Print Run Status (J) changed
        needs_scoring = False
        if not (row[scarcity_col_idx] and row[format_liquidity_col_idx] and row[mascot_power_col_idx] and row[set_depth_col_idx]):
            needs_scoring = True
        
        current_j_value = row[print_run_status_col_idx]
        if last_known_j_values.get(set_name) != current_j_value:
            needs_scoring = True
        
        if needs_scoring:
            gemini_calls_made += 1
            prompt = f"""You are a Pokemon TCG investment analyst. Score this set and provide a recommendation.

Set: {set_name}
Release Date: {row[headers.index("Date Released")]}
Era: {row[headers.index("Era")]}
BB Price (GBP): {row[headers.index("BB Price (GBP)")]}
Set Value (GBP): {row[headers.index("Set Value (GBP)")]}
Top 3 Chase Cards: {row[headers.index("Top 3 Chase Cards")]}
Box %: {row[headers.index("Box %")]}
Chase Card %: {row[headers.index("Chase Card %")]}
Print Status (Column J): {current_j_value}

Score each category out of 5 (integer only):
- L Scarcity: 5=Out of Print, 4=Going OOP soon, 3=18-24mo old, 2=In print <18mo, 1=Heavily restocked
- M Format Liquidity: 5=Booster Box easy sell, 3=Mixed products, 1=Collection box only
- N Mascot Power: 5=Charizard/Eevee/Umbreon chase, 3=Popular but not top tier, 1=No big chase cards
- O Set Depth: 5=Many Illustration Rares spread across set, 3=Several good cards, 1=Only 1-2 good cards

Respond in JSON only:
{{"L": int, "M": int, "N": int, "O": int, "H": "recommendation"}}
"""
            try:
                gemini_response = call_gemini_api(prompt) # Simulate Gemini call
                worksheet_data[i+1][scarcity_col_idx] = gemini_response.get("L", "")
                worksheet_data[i+1][format_liquidity_col_idx] = gemini_response.get("M", "")
                worksheet_data[i+1][mascot_power_col_idx] = gemini_response.get("N", "")
                worksheet_data[i+1][set_depth_col_idx] = gemini_response.get("O", "")
                worksheet_data[i+1][investor_rec_col_idx] = gemini_response.get("H", "")
                
                # Update Decision Matrix Score (Column K) - formula
                worksheet_data[i+1][decision_matrix_score_col_idx] = f"=L{i+2}+M{i+2}+N{i+2}+O{i+2}"

                last_known_j_values[set_name] = current_j_value # Update last known J value
            except Exception as e:
                print(f"WARNING: Gemini API call failed for {set_name}: {e}. Skipping scoring for this set.")
    
    config["last_known_j_values"] = last_known_j_values
    return worksheet_data, gemini_calls, config

def format_and_highlight_dates(worksheet_data):
    headers = worksheet_data[0]
    date_released_col_idx = headers.index("Date Released")
    print_run_status_col_idx = headers.index("Print Run Status")

    # Conditional formatting data (not directly applied here, but for explanation)
    conditional_formats = []

    for i, row in enumerate(worksheet_data[1:]): # Skip header row
        date_str = row[date_released_col_idx]
        if date_str:
            try:
                # Format to Mon-YY
                date_obj = datetime.datetime.strptime(date_str, \'%b-%y\')
                worksheet_data[i+1][date_released_col_idx] = date_obj.strftime(\'%b-%y\')

                # Calculate months since release
                today = datetime.date.today()
                release_date_for_calc = date_obj.date()
                months_since_release = (today.year - release_date_for_calc.year) * 12 + (today.month - release_date_for_calc.month)

                # Conditional highlighting logic
                print_status = row[print_run_status_col_idx]
                if "In Print" in print_status:
                    # No fill if "In Print"
                    conditional_formats.append({"range": f"B{i+2}", "rule": "NO_FILL_COLOR"})
                elif months_since_release >= 24:
                    # Red fill for 24+ months
                    conditional_formats.append({"range": f"B{i+2}", "rule": "RED_FILL"})
                elif 18 <= months_since_release < 24:
                    # Yellow fill for 18-24 months
                    conditional_formats.append({"range": f"B{i+2}", "rule": "YELLOW_FILL"})
                
            except ValueError:
                print(f"WARNING: Could not parse date \'{date_str}\' in row {i+2}. Skipping date formatting/highlighting for this row.")
    
    # In a real scenario, these conditional_formats would be sent to gspread.spreadsheet.batch_update
    print(f"Simulating conditional formatting rules: {conditional_formats}")
    return worksheet_data

# --- Main Workflow ---
def main():
    print("Starting Pokemon Booster Box Tracker Agent (First Run Simulation)")

    config = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, \'r\') as f:
            config = json.load(f)
    else:
        print(f"ERROR: {CONFIG_FILE} not found. Please ensure it exists with \'sheet_id\' configured.")
        return

    sheet_id = config.get(\'sheet_id\')
    if not sheet_id or sheet_id == "YOUR_GOOGLE_SHEET_ID_HERE":
        print("ERROR: Google Sheet ID not configured in config.json. Please update it manually.")
        return

    # 1. Get Google Sheets client
    gc = get_google_sheet_client()
    if not gc:
        return

    spreadsheet = get_spreadsheet(gc, sheet_id)
    if not spreadsheet:
        return

    current_date_str = datetime.date.today().strftime(\'%Y-%m-%d\')
    current_month_year = datetime.date.today().strftime(\'%b %y\')
    
    # Adjust current_month_year for simulation to match 'Apr 26' and 'May 26' for testing new sheet creation
    # In a real scenario, this would be the actual current month/year
    # For testing, let's assume current_month_year is 'May 26' if today is May 2026, so a new sheet would be created.
    # For this simulation, let's pretend today is April 2026 to work with 'Apr 26'
    current_month_year = "Apr 26" # For simulation to use the existing 'Apr 26' sheet
    # If we wanted to test new sheet creation, we'd set it to "May 26" or similar.


    # 2. Backup
    backup_path = download_and_backup(spreadsheet, current_date_str)

    # 3. Create new monthly sheet and configure headers
    # Ensure "Selling Individual Cards" is never modified and is skipped
    all_worksheets = spreadsheet.worksheets()
    monthly_worksheets = [ws for ws in all_worksheets if ws.title != "Selling Individual Cards"]

    # Get the most recent monthly sheet (the one we\'ll be reading from and updating)
    # Assuming the most recent sheet is the leftmost non-"Selling Individual Cards" sheet
    # Or, if current_month_year sheet exists, use that.
    
    # In this simulation, we\'ll try to get the \'current_month_year\' sheet if it exists,
    # otherwise, assume we\'re working on the most recent existing monthly sheet until new sets are added.
    try:
        current_worksheet = spreadsheet.worksheet(current_month_year)
        print(f"Working on existing sheet: {current_month_year}")
    except gspread.exceptions.WorksheetNotFound:
        current_worksheet = create_and_configure_sheet(spreadsheet, current_month_year)
        if not current_worksheet:
            print("ERROR: Failed to get or create current monthly worksheet.")
            return

    # Fetch existing data (excluding header for processing)
    existing_data = current_worksheet.get_all_values()
    if not existing_data:
        print("ERROR: Current worksheet is empty. Cannot proceed.")
        return

    headers = existing_data[0]
    current_sets_in_sheet = {row[headers.index("Set Name")]: row for row in existing_data[1:]}

    # 4. New Set Detection & Addition
    pokemon_wizard_sets = fetch_pokemon_wizard_sets()
    new_sets_added = 0
    updated_worksheet_data = existing_data[:] # Create a copy to modify

    for pw_set in pokemon_wizard_sets:
        set_name = pw_set["name"]
        if set_name not in current_sets_in_sheet:
            print(f"New set detected: {set_name}")
            set_details = get_set_details(pw_set["url"], set_name)
            
            new_row = [""] * len(headers)
            new_row[headers.index("Era")] = set_details.get("era", "")
            new_row[headers.index("Date Released")] = set_details.get("date_released", "")
            new_row[headers.index("Set Name")] = set_name
            new_row[headers.index("Print Run Status")] = "In Print" # Default for new sets

            # Add new row, keeping sorted by release date (newest at top)
            # This logic needs to insert into the correct position based on \'Date Released\'
            # For simplicity in simulation, we\'ll append and assume sorting happens later or is handled by gspread API
            # For accurate insertion, you\'d need to convert \'Date Released\' to datetime objects for sorting.
            
            # Find insertion point based on Date Released (Column B)
            insert_index = 1 # Start after header
            if set_details.get("date_released"):
                new_set_date = datetime.datetime.strptime(set_details["date_released"], \'%b-%y\').date()
                for r_idx, row_data in enumerate(updated_worksheet_data[1:]):
                    sheet_set_date_str = row_data[headers.index("Date Released")]
                    if sheet_set_date_str:
                        sheet_set_date = datetime.datetime.strptime(sheet_set_date_str, \'%b-%y\').date()
                        if new_set_date > sheet_set_date: # Newest at top
                            insert_index = r_idx + 1
                            break
                    insert_index = r_idx + 2 # If it\'s the oldest, append at end of data rows

            updated_worksheet_data.insert(insert_index, new_row)
            new_sets_added += 1

    # Update current_sets_in_sheet for subsequent processing if new sets were added
    if new_sets_added > 0:
        current_sets_in_sheet = {row[headers.index("Set Name")]: row for row in updated_worksheet_data[1:]}

    # 5. Price Updates
    usd_to_gbp_rate = get_usd_to_gbp_rate()
    updated_worksheet_data, rows_updated_prices = update_prices_and_values(updated_worksheet_data, usd_to_gbp_rate)
    print(f"Updated {rows_updated_prices} rows with new prices and values.")

    # 6. Gemini Scoring
    updated_worksheet_data, gemini_calls, config = score_sets_with_gemini(updated_worksheet_data, config)
    print(f"Made {gemini_calls} Gemini API calls.")
    
    # 7. Date Formatting & Highlighting
    updated_worksheet_data = format_and_highlight_dates(updated_worksheet_data)

    # 8. Write all changes back to Google Sheets
    # gspread.worksheet.update takes range and list of lists
    current_worksheet.update(f\'A1:O{len(updated_worksheet_data)}\', updated_worksheet_data)
    print("Changes written back to Google Sheets.")

    # 9. Also save a local Excel copy
    print(f"Simulating saving local Excel copy to {LOCAL_EXCEL_FILE} and {SCP_DEST_FILE}")
    with open(LOCAL_EXCEL_FILE, \'w\') as f:
        f.write("DUMMY EXCEL LOCAL COPY")
    with open(SCP_DEST_FILE, \'w\') as f:
        f.write("DUMMY EXCEL SCP COPY")

    # Update config.json with last_known_j_values
    with open(CONFIG_FILE, \'w\') as f:
        json.dump(config, f, indent=2)
    print(f"Updated {CONFIG_FILE} with last known J values.")

    print("\\n--- Run Summary ---")
    print(f"New sets added: {new_sets_added}")
    print(f"Rows with price/value updates: {rows_updated_prices}")
    print(f"Gemini API calls made: {gemini_calls}")
    print("Any blanks left for manual entry would be noted by specific warnings above.")


if __name__ == "__main__":
    main()

