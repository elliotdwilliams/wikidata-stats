import requests
import datetime
import calendar
import sys
import json

# The endpoint for the Wikidata MediaWiki API
API_ENDPOINT = "https://www.wikidata.org/w/api.php"

def get_user_input():
    """
    Prompts the user for their username and desired date range.
    Handles input validation and date parsing.

    Returns:
        tuple: A tuple containing (username, start_datetime, end_datetime).
    """
    # --- Get Username ---
    username = input("Enter your Wikidata username: ")
    if not username:
        print("Username cannot be empty.")
        sys.exit(1)

    # --- Get Date Range Type ---
    while True:
        print("\nSelect a date range option:")
        print("  1. A specific month (e.g., 2023-10)")
        print("  2. A custom date range (e.g., from 2023-10-15 to 2023-11-15)")
        choice = input("Enter your choice (1 or 2): ")
        if choice in ['1', '2']:
            break
        else:
            print("Invalid choice. Please enter 1 or 2.")

    # --- Process Date Input ---
    start_dt = None
    end_dt = None

    if choice == '1':
        # --- Handle Specific Month ---
        while True:
            month_str = input("Enter the month in YYYY-MM format: ")
            try:
                year, month = map(int, month_str.split('-'))
                # Get the first day of the month
                start_dt = datetime.datetime(year, month, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
                # Get the last day of the month
                last_day = calendar.monthrange(year, month)[1]
                end_dt = datetime.datetime(year, month, last_day, 23, 59, 59, tzinfo=datetime.timezone.utc)
                break
            except ValueError:
                print("Invalid format. Please use YYY-MM.")
    else:
        # --- Handle Custom Date Range ---
        while True:
            start_str = input("Enter the start date (YYYY-MM-DD): ")
            try:
                start_dt = datetime.datetime.fromisoformat(start_str + "T00:00:00").replace(tzinfo=datetime.timezone.utc)
                break
            except ValueError:
                print("Invalid format. Please use YYYY-MM-DD.")
        
        while True:
            end_str = input("Enter the end date (YYYY-MM-DD): ")
            try:
                # End of the day is used to include all contributions on the end date
                end_dt = datetime.datetime.fromisoformat(end_str + "T23:59:59").replace(tzinfo=datetime.timezone.utc)
                if end_dt < start_dt:
                    print("End date cannot be before the start date.")
                    continue
                break
            except ValueError:
                print("Invalid format. Please use YYYY-MM-DD.")

    return username, start_dt, end_dt


def fetch_contributions(username, start_dt, end_dt):
    """
    Fetches all contributions for a user from the Wikidata API within a given
    date range. Handles API pagination automatically.

    Args:
        username (str): The Wikidata username.
        start_dt (datetime): The start of the date range.
        end_dt (datetime): The end of the date range.

    Returns:
        list: A list of contribution dictionaries from the API, or None if an error occurs.
    """
    print(f"\nFetching contributions for '{username}'...")
    
    # Use a session for connection pooling and to set a User-Agent
    session = requests.Session()
    session.headers.update({
        'User-Agent': f'WikidataStatsScript/1.0 (mailto:user@example.com; User:{username})'
    })
    
    all_contributions = []
    
    # API parameters - FIXED: Ensure flags are included in the response
    params = {
        "action": "query",
        "format": "json",
        "list": "usercontribs",
        "ucuser": username,
        "uclimit": "500",  # Max limit per request
        "ucprop": "title|timestamp|flags|comment|parsedcomment|ids|size|sizediff|tags",
        "ucdir": "newer", # Process chronologically from start to end
        "ucstart": start_dt.isoformat(),
        "ucend": end_dt.isoformat(),
        "formatversion": "2"
    }

    try:
        while True:
            response = session.get(url=API_ENDPOINT, params=params)
            response.raise_for_status()  # Raise an exception for bad status codes
            data = response.json()

            if "error" in data:
                print(f"API Error: {data['error']['info']}")
                return None
            
            contribs = data.get("query", {}).get("usercontribs", [])
            all_contributions.extend(contribs)
            
            # Check for the 'continue' element to handle pagination
            if "continue" in data:
                params["uccontinue"] = data["continue"]["uccontinue"]
                print(f"  ...fetched {len(all_contributions)} contributions so far...")
            else:
                # No more pages
                break
    
    except requests.exceptions.RequestException as e:
        print(f"An error occurred during the API request: {e}")
        return None
        
    print(f"Total contributions found in period: {len(all_contributions)}")
    return all_contributions


def is_page_creation(contrib):
    """
    Determines if a contribution represents a page creation.
    This function handles various ways the 'new' flag might be represented.
    
    Args:
        contrib (dict): A single contribution from the API
        
    Returns:
        bool: True if this is a page creation, False otherwise
    """
    # Method 1: Check if 'new' key exists and is True (most reliable)
    if contrib.get('new', False) is True:
        return True
    
    # Method 2: Check if 'new' is in the flags list/array
    flags = contrib.get('flags', [])
    if isinstance(flags, list) and 'new' in flags:
        return True
    
    # Method 3: Check for absence of parentid - new pages don't have parent revisions
    # This is more reliable than the size method
    if contrib.get('parentid') is None or contrib.get('parentid') == 0:
        # Double-check this isn't just missing data by ensuring we have other expected fields
        if contrib.get('revid') and contrib.get('size'):
            return True
    
    # Method 4: Check by revision ID pattern - sometimes new pages can be identified
    # by having a revid but no meaningful parent revision context
    # Only use this as a last resort and with additional checks
    revid = contrib.get('revid')
    parentid = contrib.get('parentid')
    if revid and parentid and (revid - parentid == 1):
        # This might indicate a new page, but it's not reliable enough on its own
        # Only use if we have other supporting evidence
        pass
        
    return False


def process_contributions(contributions):
    """
    Processes the list of contributions to count created vs. edited pages.

    Args:
        contributions (list): A list of contribution data from the API.

    Returns:
        tuple: A tuple containing (created_count, edited_count).
    """
    if not contributions:
        return 0, 0

    # Using sets to automatically handle uniqueness of page titles (Q-IDs)
    created_pages = set()
    edited_pages = set()

    print("\nAnalyzing contributions...")

    for contrib in contributions:
        # We are only interested in contributions to the main namespace (items)
        if contrib.get("ns") == 0:
            title = contrib["title"]
            
            # Use our improved page creation detection
            is_new_page = is_page_creation(contrib)
            
            if is_new_page:
                created_pages.add(title)
            else:
                edited_pages.add(title)
    
    # To enforce the mutual exclusivity rule, we remove any pages that were
    # created in the period from the set of edited pages.
    # This ensures a page is only ever counted as "Created".
    final_edited_pages = edited_pages - created_pages
    
    print(f"  Pages created: {len(created_pages)}")
    print(f"  Pages edited (excluding created): {len(final_edited_pages)}")
    
    return len(created_pages), len(final_edited_pages)


def write_report(username, start_dt, end_dt, created_count, edited_count):
    """
    Writes the final statistics to the console and a text file.

    Args:
        username (str): The user's name.
        start_dt (datetime): The start date of the report period.
        end_dt (datetime): The end date of the report period.
        created_count (int): The count of created pages.
        edited_count (int): The count of edited pages.
    """
    start_str = start_dt.strftime("%Y-%m-%d")
    end_str = end_dt.strftime("%Y-%m-%d")

    # --- Prepare the report content ---
    report_content = (
        f"User: {username}\n"
        f"Period: {start_str} to {end_str}\n"
        f"Edited: {edited_count}\n"
        f"Created: {created_count}\n"
    )

    # --- Print to console ---
    print("\n--- Wikidata Contribution Report ---")
    print(report_content)

    # --- Write to file ---
    filename = f"wikidata_stats-{username}-{start_str}_to_{end_str}.txt"
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(report_content)
        print(f"Report successfully saved to '{filename}'")
    except IOError as e:
        print(f"Error: Could not write report to file: {e}")


def main():
    """Main function to run the script."""
    print("--- Wikidata Contribution Statistics Reporter ---")
    
    # 1. Get user input
    username, start_dt, end_dt = get_user_input()
    
    # 2. Fetch data from API
    contributions = fetch_contributions(username, start_dt, end_dt)
    
    if contributions is None:
        print("\nCould not retrieve contributions. Exiting.")
        return # Exit if fetching failed
        
    # 3. Process the data
    created_count, edited_count = process_contributions(contributions)
    
    # 4. Write the report
    write_report(username, start_dt, end_dt, created_count, edited_count)


if __name__ == "__main__":
    main()
