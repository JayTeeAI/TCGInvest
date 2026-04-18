import json
import os
import datetime
import gspread
from gspread.exceptions import WorksheetNotFound

# --- Configuration & Helpers ---
CONFIG_FILE = "/root/.openclaw/workspace/config.json"
CREDENTIALS_FILE = "/root/.openclaw/workspace/google-credentials.json"

def get_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

# --- Google Sheets Read/Write Functions ---
def get_google_sheet_client():
    """Authenticates with Google Sheets using a service account and returns a gspread client."""
    try:
        gc = gspread.service_account(filename=CREDENTIALS_FILE)
        print("Successfully authenticated with Google Sheets.")
        return gc
    except Exception as e:
        print(f"ERROR: Failed to authenticate with Google Sheets. Make sure {CREDENTIALS_FILE} is valid. Error: {e}")
        return None

def get_spreadsheet(client, sheet_id):
    """Opens a Google Spreadsheet by its ID."""
    try:
        spreadsheet = client.open_by_key(sheet_id)
        print(f"Successfully opened Google Spreadsheet with ID: {sheet_id}")
        return spreadsheet
    except Exception as e:
        print(f"ERROR: Could not open Google Sheet with ID {sheet_id}. Error: {e}")
        return None

def get_current_month_worksheet(spreadsheet, current_month_year):
    """
    Gets the worksheet for the current month. If it doesn't exist, it creates it,
    configures the header row, and moves it to the first position.
    It explicitly avoids modifying the 'Selling Individual Cards' sheet.
    """
    headers = ["Era", "Date Released", "Set Name", "BB Price (GBP)", "Set Value (GBP)", "Top 3 Chase Cards", "Box %", "Investor Recommendation", "Chase Card %", "Print Run Status", "Decision Matrix Score", "Scarcity", "Format Liquidity", "Mascot Power", "Set Depth"]
    
    try:
        worksheet = spreadsheet.worksheet(current_month_year)
        print(f"Found existing worksheet: {current_month_year}")
        # Ensure headers and basic filter are present even if sheet existed
        worksheet.update('A1:O1', [headers])
        worksheet.format('A1:O1', {
            'textFormat': {'bold': True},
            'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9} # Light gray background
        })
        worksheet.set_basic_filter('A1:O1')

    except WorksheetNotFound:
        print(f"Worksheet \'{current_month_year}\' not found. Creating new worksheet.")
        # Create new sheet with initial rows/cols (gspread requires this)
        worksheet = spreadsheet.add_worksheet(title=current_month_year, rows=100, cols=len(headers))
        
        # Move to position 0 (leftmost) if not 'Selling Individual Cards'
        if worksheet.title != "Selling Individual Cards":
            spreadsheet.move_worksheet(worksheet, 0)
            print(f"Moved \'{worksheet.title}\' to the first position.")

        # Set headers
        worksheet.update('A1:O1', [headers])

        # Apply formatting to header row
        worksheet.format('A1:O1', {
            'textFormat': {'bold': True},
            'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9} # Light gray background
        })
        
        # Set basic filter (assuming first row is headers)
        worksheet.set_basic_filter('A1:O1')
        print(f"Configured headers and filters for new sheet \'{current_month_year}'.")

    return worksheet

def read_all_data_from_sheet(worksheet):
    """Reads all cell values from a given worksheet."""
    try:
        data = worksheet.get_all_values()
        print(f"Successfully read {len(data)} rows from worksheet \'{worksheet.title}'.")
        return data
    except Exception as e:
        print(f"ERROR: Could not read data from worksheet \'{worksheet.title}\'. Error: {e}")
        return []

def write_updated_data_to_sheet(worksheet, updated_data):
    """Writes a list of lists (updated_data) to the specified worksheet."""
    if not updated_data:
        print(f"WARNING: No data to write to worksheet \'{worksheet.title}\'.")
        return

    try:
        # Ensure the worksheet is large enough for the data
        rows_needed = len(updated_data)
        cols_needed = len(updated_data[0]) if updated_data else 0
        if worksheet.row_count < rows_needed or worksheet.col_count < cols_needed:
            worksheet.resize(rows=rows_needed + 5, cols=cols_needed) # Add a buffer of 5 rows
            print(f"Resized worksheet \'{worksheet.title}\' to accommodate {rows_needed} rows and {cols_needed} columns.")

        # Update the entire range with the new data
        # gspread.worksheet.update expects a list of lists
        worksheet.update(f'A1:{(gspread.utils.rowcol_to_a1(rows_needed, cols_needed))}', updated_data)
        print(f"Successfully wrote {len(updated_data)} rows to worksheet \'{worksheet.title}\'.")
        return True
    except Exception as e:
        print(f"ERROR: Could not write data to worksheet \'{worksheet.title}\'. Error: {e}")
        return False

# Example Usage (for demonstration, not part of the requested script)
if __name__ == "__main__":
    print("--- Demonstrating Google Sheets Functions ---")
    
    # Simulate config with a placeholder sheet_id
    test_config = {"sheet_id": "YOUR_GOOGLE_SHEET_ID_HERE", "last_known_j_values": {}}
    save_config(test_config)
    print(f"Created dummy {CONFIG_FILE} with sheet_id: {test_config[\'sheet_id\']}")

    # In a real scenario, you'd replace this with your actual sheet ID
    # and ensure google-credentials.json is present.

    # Try to connect and open spreadsheet
    gc = get_google_sheet_client()
    if gc:
        sheet_id = get_config().get("sheet_id")
        if sheet_id and sheet_id != "YOUR_GOOGLE_SHEET_ID_HERE":
            spreadsheet = get_spreadsheet(gc, sheet_id)
            if spreadsheet:
                current_month_year = datetime.date.today().strftime('%b %y')
                # For testing, let's assume a specific month if needed, e.g., current_month_year = "Apr 26"
                
                # Get or create the current month's worksheet
                current_worksheet = get_current_month_worksheet(spreadsheet, current_month_year)
                
                if current_worksheet:
                    # Read data
                    data = read_all_data_from_sheet(current_worksheet)
                    if data:
                        print("First 3 rows of data:")
                        for row in data[:3]:
                            print(row)

                        # Simulate an update (e.g., change a value in the second row, third column)
                        if len(data) > 1 and len(data[1]) > 2:
                            original_value = data[1][2]
                            data[1][2] = f"Modified {original_value}"
                            print(f"Simulating update: changed data[1][2] to \'{data[1][2]}\'.")
                            write_updated_data_to_sheet(current_worksheet, data)
                    else:
                        print("No data found in the worksheet.")
                else:
                    print("Failed to get/create current month's worksheet.")
            else:
                print("Failed to open spreadsheet.")
        else:
            print("Please update 'YOUR_GOOGLE_SHEET_ID_HERE' in config.json with a valid Google Sheet ID and ensure google-credentials.json is present.")
    else:
        print("Failed to get Google Sheets client.")

    # Clean up dummy config file
    os.remove(CONFIG_FILE)
    print(f"Removed dummy {CONFIG_FILE}.")
