import kagglehub
import os
import shutil
import glob

# Download latest version
path = kagglehub.dataset_download("mtalaltariq/paysim-data")

# Find any .csv file in the downloaded directory
csv_files = glob.glob(os.path.join(path, "*.csv"))

if not csv_files:
    print("❌ No CSV files found in the dataset directory!")
else:
    # Use the first CSV found
    csv_file = csv_files[0]
    target_dir = "scripts/data"
    os.makedirs(target_dir, exist_ok=True)
    
    shutil.copy(csv_file, os.path.join(target_dir, "paysim.csv"))
    print(f"✅ Successfully copied {os.path.basename(csv_file)} to {target_dir}/paysim.csv")