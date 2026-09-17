import streamlit as st
import pandas as pd
import re
import io

def parse_dbml_to_df(dbml_input):
    """Parses DBML text and returns a pandas DataFrame with relationship details."""
    table_pattern = re.compile(r"Table\s+(\w+)\s*\{([^}]+)\}")
    schema = {}
    
    for match in table_pattern.finditer(dbml_input):
        table_name = match.group(1)
        columns_block = match.group(2)
        schema[table_name] = {}
        
        for line in columns_block.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 2:
                col_name = parts[0]
                col_type = parts[1]
                is_pk = 'Yes' if '[pk]' in line.lower() else 'No'
                schema[table_name][col_name] = {'type': col_type, 'is_pk': is_pk}

    ref_pattern = re.compile(r"Ref:\s*(\w+)\.(\w+)\s*([><-]{1,2})\s*(\w+)\.(\w+)")
    parsed_data = []
    
    for line in dbml_input.splitlines():
        line = line.strip()
        if line.startswith("Ref:"):
            match = ref_pattern.match(line)
            if match:
                table1, col1, operator, table2, col2 = match.groups()
                
                if operator == '>':
                    cardinality = "Many-to-One (N:1)"
                elif operator == '<':
                    cardinality = "One-to-Many (1:N)"
                elif operator == '-':
                    cardinality = "One-to-One (1:1)"
                elif operator == '<>':
                    cardinality = "Many-to-Many (N:M)"
                else:
                    cardinality = "Unknown"
                
                t1_col_info = schema.get(table1, {}).get(col1, {'type': 'Unknown', 'is_pk': 'Unknown'})
                t2_col_info = schema.get(table2, {}).get(col2, {'type': 'Unknown', 'is_pk': 'Unknown'})
                
                parsed_data.append({
                    "Table 1": table1,
                    "Table 1 Column": col1,
                    "Table 2": table2,
                    "Table 2 Column": col2,
                    "Cardinality": cardinality,
                    "Table 1 Column Type": t1_col_info['type'],
                    "Table 2 Column Type": t2_col_info['type'],
                    "Target is PK?": t2_col_info['is_pk']
                })

    return pd.DataFrame(parsed_data)

def to_excel_bytes(df):
    """Converts a pandas DataFrame to an Excel file in memory with formatting."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Relationships')
        
        # Access the underlying openpyxl worksheet
        worksheet = writer.sheets['Relationships']
        
        # 1. Freeze the first row
        worksheet.freeze_panes = 'A2'
        
        # 2. Enable filtering for all columns
        worksheet.auto_filter.ref = worksheet.dimensions
        
        # 3. Bold headers & auto-adjust column widths for readability
        from openpyxl.styles import Font
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            
            for cell in column:
                # Bold the first row (headers)
                if cell.row == 1:
                    cell.font = Font(bold=True)
                
                # Calculate the max length of data in the column
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            
            # Set the column width (+2 for a little padding)
            worksheet.column_dimensions[column_letter].width = max_length + 2

    return output.getvalue()

# --- Streamlit UI ---
st.set_page_config(page_title="DBML to Excel Extractor", layout="wide")

st.title("🗄️ DBML Relationship Extractor")
st.write("Paste your DBML code, filter the extracted relationships, and download the results as an Excel file.")

# 1. Input Section
dbml_input = st.text_area("Paste your DBML code here:", height=200)

if st.button("Process DBML", type="primary"):
    if not dbml_input.strip():
        st.error("Please paste some DBML code first.")
    else:
        df = parse_dbml_to_df(dbml_input)
        if df.empty:
            st.warning("No relationships (`Ref:` lines) were found.")
        else:
            # Store dataframe in session state so filters don't erase it
            st.session_state['raw_df'] = df
            st.success(f"Successfully extracted {len(df)} relationships!")

# 2. Filter and Display Section (Only shows if data has been processed)
if 'raw_df' in st.session_state:
    st.divider()
    df = st.session_state['raw_df']
    
    st.subheader("🔎 Filter Relationships")
    
    # Create dynamic columns for filters (4 filters per row)
    filter_cols = st.columns(4)
    active_filters = {}
    
    # Generate a multiselect dropdown for every column in the dataframe
    for i, column in enumerate(df.columns):
        with filter_cols[i % 4]:
            unique_values = sorted(df[column].astype(str).unique())
            selected = st.multiselect(f"Filter by {column}:", options=unique_values)
            if selected:
                active_filters[column] = selected

    # Apply all selected filters to a copied dataframe
    filtered_df = df.copy()
    for col, selected_values in active_filters.items():
        filtered_df = filtered_df[filtered_df[col].astype(str).isin(selected_values)]
        
    st.write(f"**Showing {len(filtered_df)} of {len(df)} relationships:**")
    
    # Display the filtered interactive table
    st.dataframe(filtered_df, use_container_width=True, hide_index=True)
    
    # 3. Download Section
    st.subheader("📥 Export")
    st.write("Download the current table (including your active filters) to Excel.")
    
    excel_data = to_excel_bytes(filtered_df)
    st.download_button(
        label="Download Filtered Excel File",
        data=excel_data,
        file_name="Filtered_Database_Relationships.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )