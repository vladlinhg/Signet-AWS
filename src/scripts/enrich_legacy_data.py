import csv
import os

def enrich_data():
    legacy_path = 'd:/Signet/src/data/legacy_data.csv'
    enhanced_path = 'd:/Signet/src/data/enhanced_legacy_data.csv'
    output_path = 'd:/Signet/src/data/complete_legacy_data.csv'

    # Build Tour Code Map
    tour_map = {}
    with open(legacy_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Col: Tour Code/Name
            raw_field = row.get('Tour Code/Name', '')
            if '/' in raw_field:
                parts = raw_field.split('/', 1)
                code = parts[0].strip()
                desc = parts[1].strip()
                if code and desc:
                    tour_map[code] = desc

    print(f"Loaded {len(tour_map)} tour descriptions.")

    # Process Enhanced Data
    with open(enhanced_path, 'r', encoding='utf-8-sig') as f_in, \
         open(output_path, 'w', encoding='utf-8-sig', newline='') as f_out:

        reader = csv.DictReader(f_in)
        fieldnames = reader.fieldnames + ['Tour_Description']
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()

        count = 0
        for row in reader:
            code = row.get('Tour_Code', '').strip()
            desc = tour_map.get(code, '')

            # Fallback: Try matching by Invoice if Tour match fails? (Optional, user asked for Tour match)
            # Actually, try case insensitive match
            if not desc:
                # Try explicit mappings if any known issues
                pass

            row['Tour_Description'] = desc
            writer.writerow(row)
            count += 1

    print(f"Enriched {count} rows. Saved to {output_path}")

if __name__ == "__main__":
    enrich_data()
