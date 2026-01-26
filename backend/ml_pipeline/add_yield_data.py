import os
from datetime import datetime, timedelta
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# MongoDB connection
client = MongoClient(os.getenv('MONGODB_URI'))
db = client[os.getenv('MONGODB_DB', 'cropiot')]
yield_collection = db['yield_records']
sensor_collection = db['sensor_data']

def add_yield_record(sensor_id, harvest_date, yield_value, crop_type='tobacco', unit='kg/hectare'):
    """
    Add a single yield record to MongoDB
    
    Args:
        sensor_id: ID of the sensor/location where crop was grown
        harvest_date: Date when crop was harvested (datetime or string 'YYYY-MM-DD')
        yield_value: Actual yield amount (e.g., 2500 for 2500 kg/hectare)
        crop_type: Type of crop (default: 'tobacco')
        unit: Unit of measurement (default: 'kg/hectare')
    """
    if isinstance(harvest_date, str):
        harvest_date = datetime.strptime(harvest_date, '%Y-%m-%d')
    
    record = {
        'sensor_id': sensor_id,
        'harvest_date': harvest_date,
        'yield_value': float(yield_value),
        'crop_type': crop_type,
        'unit': unit,
        'created_at': datetime.now()
    }
    
    result = yield_collection.insert_one(record)
    print(f"✓ Added yield record: {sensor_id} - {yield_value} {unit} on {harvest_date.date()}")
    return result.inserted_id

def generate_sample_yield_data(num_records=10):
    """
    Generate sample yield data for testing purposes
    Uses existing sensor IDs from your database
    """
    # Get existing sensor IDs
    sensor_ids = sensor_collection.distinct('sensor_id')
    
    if not sensor_ids:
        print("❌ No sensors found in database. Add sensor readings first.")
        return
    
    print(f"Found {len(sensor_ids)} sensors. Generating sample yield data...")
    
    import random
    
    # Generate yield records for the past 6 months
    base_date = datetime.now() - timedelta(days=180)
    
    for i in range(num_records):
        sensor_id = random.choice(sensor_ids)
        # Random harvest date in the past 6 months
        days_offset = random.randint(0, 180)
        harvest_date = base_date + timedelta(days=days_offset)
        
        # Random yield between 1500-3500 kg/hectare (typical tobacco yield range)
        yield_value = random.uniform(1500, 3500)
        
        add_yield_record(
            sensor_id=sensor_id,
            harvest_date=harvest_date,
            yield_value=yield_value,
            crop_type='tobacco',
            unit='kg/hectare'
        )
    
    print(f"\n✓ Generated {num_records} sample yield records")
    print(f"Total yield records in database: {yield_collection.count_documents({})}")

def import_yield_csv(csv_path):
    """
    Import yield data from CSV file
    
    CSV format:
    sensor_id,harvest_date,yield_value,crop_type,unit
    SENSOR_001,2024-06-15,2800,tobacco,kg/hectare
    SENSOR_002,2024-07-20,3200,tobacco,kg/hectare
    """
    import csv
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            add_yield_record(
                sensor_id=row['sensor_id'],
                harvest_date=row['harvest_date'],
                yield_value=float(row['yield_value']),
                crop_type=row.get('crop_type', 'tobacco'),
                unit=row.get('unit', 'kg/hectare')
            )
            count += 1
    
    print(f"\n✓ Imported {count} yield records from {csv_path}")

def view_yield_records(limit=10):
    """View recent yield records"""
    records = yield_collection.find().sort('harvest_date', -1).limit(limit)
    
    print(f"\n📊 Recent Yield Records (showing {limit}):")
    print("-" * 80)
    for record in records:
        print(f"Sensor: {record['sensor_id']}")
        print(f"  Harvest Date: {record['harvest_date'].date()}")
        print(f"  Yield: {record['yield_value']:.2f} {record['unit']}")
        print(f"  Crop: {record['crop_type']}")
        print()

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python add_yield_data.py generate [num_records]  - Generate sample data")
        print("  python add_yield_data.py add <sensor_id> <date> <yield>  - Add single record")
        print("  python add_yield_data.py import <csv_file>  - Import from CSV")
        print("  python add_yield_data.py view [limit]  - View records")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'generate':
        num = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        generate_sample_yield_data(num)
        view_yield_records(5)
    
    elif command == 'add':
        if len(sys.argv) < 5:
            print("Usage: python add_yield_data.py add <sensor_id> <date> <yield>")
            sys.exit(1)
        add_yield_record(sys.argv[2], sys.argv[3], float(sys.argv[4]))
    
    elif command == 'import':
        if len(sys.argv) < 3:
            print("Usage: python add_yield_data.py import <csv_file>")
            sys.exit(1)
        import_yield_csv(sys.argv[2])
    
    elif command == 'view':
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        view_yield_records(limit)
    
    else:
        print(f"Unknown command: {command}")
