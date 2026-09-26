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

    df = pd.DataFrame(parsed_data)
    
    if not df.empty:
        # Create Filter 1 (Tables) and Filter 2 (Columns) by sorting alphabetically and joining
        # Sorting ensures that "A" and "B" always becomes "A-B", ignoring the original order.
        df.insert(0, 'Filter 1 (Tables)', df.apply(lambda x: "-".join(sorted([x['Table 1'], x['Table 2']])), axis=1))
        df.insert(1, 'Filter 2 (Columns)', df.apply(lambda x: "-".join(sorted([x['Table 1 Column'], x['Table 2 Column']])), axis=1))
        
    return df

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
                if cell.row == 1:
                    cell.font = Font(bold=True)
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
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
            st.session_state['raw_df'] = df
            st.success(f"Successfully extracted {len(df)} relationships!")

# 2. Filter and Display Section
if 'raw_df' in st.session_state:
    st.divider()
    df = st.session_state['raw_df']
    
    st.subheader("🔎 Filter Relationships")
    
    all_tables = sorted(set(df['Table 1']).union(set(df['Table 2'])))
    all_columns = sorted(set(df['Table 1 Column']).union(set(df['Table 2 Column'])))
    all_cards = sorted(df['Cardinality'].astype(str).unique())
    all_pk_statuses = sorted(df['Target is PK?'].astype(str).unique())

    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        selected_tables = st.multiselect(
            "Filter by Table (Max 2):", 
            options=all_tables, 
            max_selections=2,
            help="Select 1 table to see all its relations. Select 2 tables to see the specific relation between them."
        )
    with col2:
        selected_columns = st.multiselect("Filter by Column (Any):", options=all_columns)
    with col3:
        selected_cards = st.multiselect("Filter by Cardinality:", options=all_cards)
    with col4:
        selected_pk = st.multiselect("Filter by Target is PK?:", options=all_pk_statuses)

    # Apply all selected filters
    filtered_df = df.copy()
    
    # Table Filter Logic
    if len(selected_tables) == 1:
        t1 = selected_tables[0]
        filtered_df = filtered_df[
            (filtered_df['Table 1'] == t1) | 
            (filtered_df['Table 2'] == t1)
        ]
    elif len(selected_tables) == 2:
        t1 = selected_tables[0]
        t2 = selected_tables[1]
        filtered_df = filtered_df[
            ((filtered_df['Table 1'] == t1) & (filtered_df['Table 2'] == t2)) | 
            ((filtered_df['Table 1'] == t2) & (filtered_df['Table 2'] == t1))
        ]
        
    # Column Filter Logic
    if selected_columns:
        filtered_df = filtered_df[
            filtered_df['Table 1 Column'].isin(selected_columns) | 
            filtered_df['Table 2 Column'].isin(selected_columns)
        ]
        
    # Standard AND conditions for the rest
    if selected_cards:
        filtered_df = filtered_df[filtered_df['Cardinality'].isin(selected_cards)]
        
    if selected_pk:
        filtered_df = filtered_df[filtered_df['Target is PK?'].isin(selected_pk)]
        
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