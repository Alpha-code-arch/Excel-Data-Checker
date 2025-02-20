import streamlit as st
import pandas as pd
import time
import re

# Increase Pandas Styler limit to avoid cell rendering issues
pd.set_option("styler.render.max_elements", 8000000)

st.title("Data Checker")

# Function to clean data
def clean_data(df, base_column):
    for col in df.columns:
        df[col] = df[col].apply(lambda x: "❌" if (pd.isna(x) or x == "") and col == base_column else "-" if pd.isna(x) or x == "" else str(x).strip() if isinstance(x, str) else x)
    
    for col in df.select_dtypes(include=['float']):
        df[col] = df[col].apply(lambda x: int(x) if x == int(x) else x)
    
    df = df.astype(str)
    return df

# Function to clean strings
def clean_string(value):
    if isinstance(value, str):
        value = re.sub(r'\s+', ' ', value).strip()
    return value if value else "-"

# Function to check mismatch
def is_mismatch(value1, value2):
    value1, value2 = clean_string(value1), clean_string(value2)
    try:
        if float(value1) == float(value1):
            value1 = round(float(value1), 8)
    except ValueError:
        pass
    try:
        if float(value2) == float(value2):
            value2 = round(float(value2), 8)
    except ValueError:
        pass
    return str(value1) != str(value2)

# Function to replace matched values with "-"
def replace_matches_with_dash(df, mask, selected_columns):
    for col in selected_columns:
        df.loc[~mask[col], [f"{col}_file1", f"{col}_file2"]] = "-"
    return df

# Function to add row numbers
def add_row_number(df, file_label):
    df[f'row_number_{file_label}'] = df.index + 1  # Start from 1 instead of 0
    return df

# Upload Correct Data File
st.write("### Upload Data File")
correct_file = st.file_uploader("Upload Excel File", type=["xlsx", "csv"], key="correct_file")

if correct_file:
    with st.spinner("Reading Data File..."):
        time.sleep(1)
        file_ext = correct_file.name.split('.')[-1]
        df_correct = pd.read_excel(correct_file, engine='openpyxl') if file_ext == 'xlsx' else pd.read_csv(correct_file, low_memory=False)

    # Column Selection
    st.write("### Select Base Column for Matching")
    base_column = st.selectbox("Choose a base column to match data", list(df_correct.columns), key="base_column")

    df_correct = clean_data(df_correct, base_column)  # Clean data after base column selection
    df_correct = add_row_number(df_correct, "file1")

    st.write("### Select Columns for Checking")
    selected_columns = st.multiselect("Choose columns to compare", list(df_correct.columns), key="selected_columns")

    # Upload Data Checking File
    st.write("### Upload Excel File")
    checking_file = st.file_uploader("Upload Excel File", type=["xlsx", "csv"], key="checking_file")

    if checking_file and selected_columns and base_column:
        with st.spinner("Reading Data File..."):
            time.sleep(1)
            file_ext = checking_file.name.split('.')[-1]
            df_checking = pd.read_excel(checking_file, engine='openpyxl') if file_ext == 'xlsx' else pd.read_csv(checking_file, low_memory=False)

        df_checking = clean_data(df_checking, base_column)  # Clean data after base column selection
        df_checking = add_row_number(df_checking, "file2")

        # Separate rows where the base column is empty
        empty_base_rows_file1 = df_correct[df_correct[base_column] == "❌"].copy()
        empty_base_rows_file2 = df_checking[df_checking[base_column] == "❌"].copy()

        # Keep only base column and selected columns
        display_columns = [base_column] + selected_columns

        # Rename columns to indicate source file
        empty_base_rows_file1 = empty_base_rows_file1[display_columns].rename(columns={col: f"{col}_file1" for col in display_columns})
        empty_base_rows_file2 = empty_base_rows_file2[display_columns].rename(columns={col: f"{col}_file2" for col in display_columns})

        # Add "Source File" column before merging
        empty_base_rows_file1["Source File"] = "Correct File"
        empty_base_rows_file2["Source File"] = "Checking File"

        # Add row numbers to empty base rows
        empty_base_rows_file1 = add_row_number(empty_base_rows_file1, "file1")
        empty_base_rows_file2 = add_row_number(empty_base_rows_file2, "file2")

        # Merge both empty base column datasets (align by index)
        empty_base_combined = pd.concat([empty_base_rows_file1, empty_base_rows_file2], axis=0, ignore_index=True)

        # Remove empty base column rows from mismatch check
        df_correct_filtered = df_correct[df_correct[base_column] != "❌"]
        df_checking_filtered = df_checking[df_checking[base_column] != "❌"]

        if set(selected_columns).issubset(df_checking_filtered.columns) and base_column in df_checking_filtered.columns:
            with st.spinner("Comparing Data..."):
                time.sleep(1)

                # Merge filtered data based on the base column
                df_combined = pd.merge(df_correct_filtered, df_checking_filtered, on=base_column, how='inner', suffixes=('_file1', '_file2'))

                # Create a mask for mismatches
                mismatch_mask = pd.DataFrame(False, index=df_combined.index, columns=selected_columns)

                # Detect mismatches
                for col in selected_columns:
                    mismatch_mask[col] = df_combined[f"{col}_file1"].combine(df_combined[f"{col}_file2"], is_mismatch)

                # Filter mismatched rows
                mismatch_rows = df_combined[mismatch_mask.any(axis=1)]

                # Display mismatched data
                st.write("### Mismatched Data (Base column not empty)")
                if not mismatch_rows.empty:
                    display_columns = [base_column] + ["row_number_file2"] + [f"{col}_file2" for col in selected_columns] + ["row_number_file1"] + [f"{col}_file1" for col in selected_columns]
                    mismatch_rows_display = mismatch_rows[display_columns].copy()

                    # Replace matched data with "-"
                    mismatch_rows_display = replace_matches_with_dash(mismatch_rows_display, mismatch_mask, selected_columns)

                    # Sort by row_number_file1 to maintain original order
                    mismatch_rows_display = mismatch_rows_display.sort_values(by=["row_number_file1"])

                    st.dataframe(mismatch_rows_display)
                else:
                    st.success("No mismatched data found.")

                # Mismatch Percentage Calculation
                total_rows_correct = len(df_correct_filtered)
                mismatch_count = len(mismatch_rows)
                mismatch_percentage = (mismatch_count / total_rows_correct) * 100 if total_rows_correct > 0 else 0

                # Display Mismatch Metrics
                st.write("### Mismatch Analysis")
                st.metric(label="Mismatch Percentage", value=f"{mismatch_percentage:.2f}%", delta=f"{mismatch_count} rows mismatched")
                st.progress(mismatch_percentage / 100)

        # Display the empty base column rows separately
        if not empty_base_combined.empty:
            st.write("### Rows with Empty Base Column")
            st.dataframe(empty_base_combined)
