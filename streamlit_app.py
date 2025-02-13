import streamlit as st
import pandas as pd
import time
import re

# Increase Pandas Styler limit to avoid cell rendering issues
pd.set_option("styler.render.max_elements", 8000000)

st.title("Data Checker")

# Function to clean data
def clean_data(df):
    df = df.applymap(lambda x: str(x).strip() if isinstance(x, str) else x)
    df = df.fillna(0)
    for col in df.select_dtypes(include=['float']):
        df[col] = df[col].apply(lambda x: int(x) if x == int(x) else x)
    df = df.astype(str)
    return df

# Function to clean strings
def clean_string(value):
    if isinstance(value, str):
        value = re.sub(r'\s+', ' ', value).strip()
    return value

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
correct_file = st.file_uploader("Upload Correct Excel File", type=["xlsx", "csv"], key="correct_file")

if correct_file:
    with st.spinner("Reading Data File..."):
        time.sleep(1)
        file_ext = correct_file.name.split('.')[-1]
        df_correct = pd.read_excel(correct_file, engine='openpyxl') if file_ext == 'xlsx' else pd.read_csv(correct_file, low_memory=False)
        df_correct = clean_data(df_correct)

    # Add row number to the correct data
    df_correct = add_row_number(df_correct, "file1")

    # Column Selection
    st.write("### Select Base Column for Matching")
    base_column = st.selectbox("Choose a base column to match data", list(df_correct.columns), key="base_column")

    st.write("### Select Columns for Checking")
    selected_columns = st.multiselect("Choose columns to compare", list(df_correct.columns), key="selected_columns")

    # Upload Data Checking File
    st.write("### Upload Data Checking File")
    checking_file = st.file_uploader("Upload Data Checking Excel File", type=["xlsx", "csv"], key="checking_file")

    if checking_file and selected_columns and base_column:
        with st.spinner("Reading Data File..."):
            time.sleep(1)
            file_ext = checking_file.name.split('.')[-1]
            df_checking = pd.read_excel(checking_file, engine='openpyxl') if file_ext == 'xlsx' else pd.read_csv(checking_file, low_memory=False)
            df_checking = clean_data(df_checking)

        # Add row number to the checking data
        df_checking = add_row_number(df_checking, "file2")

        if set(selected_columns).issubset(df_checking.columns) and base_column in df_checking.columns:
            with st.spinner("Comparing Data..."):
                time.sleep(1)
                
                # Merge both files based on the base column
                df_combined = pd.merge(df_correct, df_checking, on=base_column, how='inner', suffixes=('_file1', '_file2'))

                # Create a mask for mismatches
                mismatch_mask = pd.DataFrame(False, index=df_combined.index, columns=selected_columns)

                # Detect mismatches
                for col in selected_columns:
                    mismatch_mask[col] = df_combined[f"{col}_file1"].combine(df_combined[f"{col}_file2"], is_mismatch)

                # Filter mismatched rows
                mismatch_rows = df_combined[mismatch_mask.any(axis=1)]

                # Display mismatched data
                st.write("### Mismatched Data")
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
                total_rows_correct = len(df_correct)
                mismatch_count = len(mismatch_rows)
                mismatch_percentage = (mismatch_count / total_rows_correct) * 100 if total_rows_correct > 0 else 0

                # Display Mismatch Metrics
                st.write("### Mismatch Analysis")
                st.metric(label="Mismatch Percentage", value=f"{mismatch_percentage:.2f}%", delta=f"{mismatch_count} rows mismatched")
                st.progress(mismatch_percentage / 100)