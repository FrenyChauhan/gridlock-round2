import os
import pandas as pd
import numpy as np

def run_eda():
    raw_path = os.path.join("data", "raw", "dataset", "jan to may police violation_anonymized791b166.csv")
    reports_dir = "reports"
    os.makedirs(reports_dir, exist_ok=True)
    
    print(f"Loading dataset from {raw_path}...")
    if not os.path.exists(raw_path):
        raise FileNotFoundError(f"Dataset not found at {raw_path}. Please check the folder setup.")
        
    # Read full dataset for overall stats
    df = pd.read_csv(raw_path, low_memory=False)
    n_rows, n_cols = df.shape
    print(f"Successfully loaded dataset. Shape: {n_rows} rows, {n_cols} columns.")
    
    # ── 1. Calculate General Stats ───────────────────────────────────────────
    mem_usage = df.memory_usage(deep=True).sum() / (1024 * 1024) # MB
    null_counts = df.isnull().sum()
    null_percentages = (null_counts / n_rows) * 100
    
    schema_info = []
    for col in df.columns:
        schema_info.append({
            "Column": col,
            "Dtype": str(df[col].dtype),
            "Null Count": null_counts[col],
            "Null %": f"{null_percentages[col]:.2f}%"
        })
    schema_df = pd.DataFrame(schema_info)
    
    # ── 2. Temporal Features ─────────────────────────────────────────────────
    print("Processing datetime columns...")
    df['created_datetime'] = pd.to_datetime(df['created_datetime'], errors='coerce')
    min_date = df['created_datetime'].min()
    max_date = df['created_datetime'].max()
    
    # Extract hour of day
    df['hour'] = df['created_datetime'].dt.hour
    hourly_counts = df['hour'].value_counts().sort_index()
    hourly_df = pd.DataFrame({
        "Hour": hourly_counts.index,
        "Violations": hourly_counts.values,
        "Percentage": (hourly_counts.values / n_rows) * 100
    })
    
    # ── 3. Categorical Distributions ─────────────────────────────────────────
    def get_top_n(column_name, n=10):
        counts = df[column_name].value_counts(dropna=False)
        top_n = pd.DataFrame({
            "Value": counts.index[:n],
            "Count": counts.values[:n],
            "Percentage": (counts.values[:n] / n_rows) * 100
        })
        return top_n
        
    top_violations = get_top_n("violation_type")
    top_stations = get_top_n("police_station")
    top_vehicles = get_top_n("vehicle_type")
    validation_stats = get_top_n("validation_status")
    top_junctions = get_top_n("junction_name")
    
    # ── 4. Geographical Ranges ───────────────────────────────────────────────
    # Filter out obvious coordinate outliers (e.g. 0.0 or far outside India/Bengaluru)
    valid_geo = df[(df['latitude'] > 12.0) & (df['latitude'] < 14.0) & 
                   (df['longitude'] > 77.0) & (df['longitude'] < 79.0)]
                   
    lat_min, lat_max = valid_geo['latitude'].min(), valid_geo['latitude'].max()
    lon_min, lon_max = valid_geo['longitude'].min(), valid_geo['longitude'].max()
    lat_mean, lon_mean = valid_geo['latitude'].mean(), valid_geo['longitude'].mean()
    
    # ── 5. Generate Markdown Report ──────────────────────────────────────────
    md_report_path = os.path.join(reports_dir, "eda_summary.md")
    print(f"Generating markdown summary document at {md_report_path}...")
    
    with open(md_report_path, "w", encoding="utf-8") as f:
        f.write("# Exploratory Data Analysis & Dataset Summary\n\n")
        f.write("This document summarizes the core statistics and distributions extracted from the police violation dataset.\n\n")
        
        f.write("## 1. Dataset Profile Overview\n")
        f.write(f"- **Total Rows**: {n_rows:,}\n")
        f.write(f"- **Total Columns**: {n_cols}\n")
        f.write(f"- **Memory Usage**: {mem_usage:.2f} MB\n")
        f.write(f"- **Temporal Range**: {min_date} to {max_date}\n\n")
        
        f.write("### Column Details and Missing Rates\n")
        f.write("| Column | Data Type | Null Count | Null % |\n")
        f.write("| --- | --- | --- | --- |\n")
        for idx, row in schema_df.iterrows():
            f.write(f"| `{row['Column']}` | {row['Dtype']} | {row['Null Count']:,} | {row['Null %']} |\n")
        f.write("\n")
        
        f.write("## 2. Key Categorical Distributions\n\n")
        
        f.write("### Top 10 Violation Types\n")
        f.write("| Violation Type | Count | Percentage |\n")
        f.write("| --- | --- | --- |\n")
        for idx, row in top_violations.iterrows():
            f.write(f"| {row['Value']} | {row['Count']:,} | {row['Percentage']:.2f}% |\n")
        f.write("\n")
        
        f.write("### Top 10 Police Stations\n")
        f.write("| Police Station | Count | Percentage |\n")
        f.write("| --- | --- | --- |\n")
        for idx, row in top_stations.iterrows():
            f.write(f"| {row['Value']} | {row['Count']:,} | {row['Percentage']:.2f}% |\n")
        f.write("\n")
        
        f.write("### Top 10 Vehicle Types\n")
        f.write("| Vehicle Type | Count | Percentage |\n")
        f.write("| --- | --- | --- |\n")
        for idx, row in top_vehicles.iterrows():
            f.write(f"| {row['Value']} | {row['Count']:,} | {row['Percentage']:.2f}% |\n")
        f.write("\n")
        
        f.write("### Validation Status\n")
        f.write("| Status | Count | Percentage |\n")
        f.write("| --- | --- | --- |\n")
        for idx, row in validation_stats.iterrows():
            f.write(f"| {row['Value']} | {row['Count']:,} | {row['Percentage']:.2f}% |\n")
        f.write("\n")
        
        f.write("### Top 10 Junctions\n")
        f.write("| Junction | Count | Percentage |\n")
        f.write("| --- | --- | --- |\n")
        for idx, row in top_junctions.iterrows():
            f.write(f"| {row['Value']} | {row['Count']:,} | {row['Percentage']:.2f}% |\n")
        f.write("\n")
        
        f.write("## 3. Geographical Insights\n")
        f.write("Coordinates bounding box (excluding noise outside Bengaluru area):\n")
        f.write(f"- **Latitude Range**: [{lat_min:.6f}, {lat_max:.6f}] (Mean: {lat_mean:.6f})\n")
        f.write(f"- **Longitude Range**: [{lon_min:.6f}, {lon_max:.6f}] (Mean: {lon_mean:.6f})\n")
        f.write(f"- **Total Rows with Invalid Coordinates**: {n_rows - len(valid_geo):,} ({((n_rows - len(valid_geo))/n_rows)*100:.2f}%)\n\n")
        
        f.write("## 4. Temporal Analysis: Hourly Violation Activity\n")
        f.write("| Hour of Day | Violations | Percentage |\n")
        f.write("| --- | --- | --- |\n")
        # Show a summary of active hours
        for idx, row in hourly_df.iterrows():
            f.write(f"| {int(row['Hour'])}:00 | {int(row['Violations']):,} | {row['Percentage']:.2f}% |\n")
            
    # ── 6. Run data-profiling on a sample ──────────────────────────────────
    print("Running data-profiling...")
    try:
        from data_profiling import ProfileReport
        
        # Sample 50,000 rows to keep generation fast and fit in memory
        sample_size = min(50000, n_rows)
        print(f"Sampling {sample_size} rows for interactive HTML profiling...")
        sample_df = df.sample(n=sample_size, random_state=42)
        
        profile = ProfileReport(
            sample_df,
            title="Traffic Violations Profile Report (50K Sample)",
            explorative=True,
            minimal=True # Disable expensive correlations to guarantee fast rendering
        )
        
        html_report_path = os.path.join(reports_dir, "dataset_profile_report.html")
        profile.to_file(html_report_path)
        print(f"Interactive HTML profiling report generated successfully at {html_report_path}")
        
        # Patch the generated HTML to fix optional chaining and the jQuery-like click syntax error
        if os.path.exists(html_report_path):
            print("Patching HTML report to fix syntax errors (optional chaining & .click())...")
            with open(html_report_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            
            bad_syntax_1 = 'document.querySelector("#toggle-correlation-description")?.click(() => {'
            bad_syntax_2 = 'document.querySelector("#toggle-correlation-description")?.addEventListener("click", () => {'
            
            good_syntax = 'const toggleBtn = document.querySelector("#toggle-correlation-description"); toggleBtn && toggleBtn.addEventListener("click", () => {'
            
            patched = False
            if bad_syntax_1 in html_content:
                html_content = html_content.replace(bad_syntax_1, good_syntax)
                patched = True
            if bad_syntax_2 in html_content:
                html_content = html_content.replace(bad_syntax_2, good_syntax)
                patched = True
                
            if patched:
                with open(html_report_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                print("HTML report successfully patched with ES5/ES6 compliant click event handler.")
            else:
                print("Syntax pattern not found or already patched.")
                
    except ImportError:
        print("[ERROR] data_profiling is not installed. Skipping HTML report generation.")
        print("Please check your python package environment.")
    except Exception as e:
        print(f"[ERROR] Failed to generate data_profiling HTML report: {e}")

if __name__ == "__main__":
    run_eda()
