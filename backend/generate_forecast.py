import pandas as pd
from prophet import Prophet
import os
import sys

# Check if the input file exists
if not os.path.exists('dump.csv'):
    print("❌ Error: 'dump.csv' file not found in the current directory!")
    sys.exit(1)

try:
    # Load CSV and strip any unwanted spaces from column names
    df = pd.read_csv('dump.csv')
    df.columns = df.columns.str.strip()  # Remove leading/trailing spaces from column names

    # Debug: Check columns and ensure correct ones
    print("🔍 Columns found:", df.columns.tolist())

    # Ensure that 'index_name' and 'index_date' columns exist and use them
    if 'index_name' not in df.columns or 'index_date' not in df.columns or 'closing_index_value' not in df.columns:
        print("❌ Required columns ('index_name', 'index_date', 'closing_index_value') not found! Please check your CSV file.")
        sys.exit(1)

    # Extract unique index names from the 'index_name' column
    index_names = df['index_name'].dropna().unique()

    # Directory to save forecast files
    output_dir = 'forecast_output'
    os.makedirs(output_dir, exist_ok=True)

    # Loop through each index_name and generate forecast
    for index_name in index_names:
        try:
            # Filter data for the current index_name and select relevant columns
            index_data = df[df['index_name'] == index_name][['index_date', 'closing_index_value']].dropna()

            # Skip index_names with no data
            if index_data.empty:
                print(f"⚠️ No data found for index: {index_name}")
                continue

            # Rename columns to fit Prophet's expected format
            index_data.columns = ['ds', 'y']
            
            # Convert 'ds' (index_date) to datetime, automatically handling different formats
            index_data['ds'] = pd.to_datetime(index_data['ds'], errors='coerce', dayfirst=False)
            
            # Drop any rows where the 'ds' column could not be parsed
            index_data = index_data.dropna(subset=['ds'])
            
            # Train the model
            model = Prophet()
            model.fit(index_data)

            # Make future predictions (next 30 days)
            future = model.make_future_dataframe(periods=30)  # Fixed: removed incorrect data parameter
            forecast = model.predict(future)

            # Save forecasted data to a CSV file
            forecast[['ds', 'yhat']].to_csv(f"{output_dir}/{index_name}.csv", index=False)
            print(f"✅ Forecast generated for {index_name}")

        except Exception as e:
            print(f"❌ Error processing {index_name}: {str(e)}")
            continue

    print("✅ All forecasts completed.")

except Exception as e:
    print(f"❌ An error occurred: {str(e)}")
    sys.exit(1)
