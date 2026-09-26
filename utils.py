import pandas as pd
import re
import io

def parse_dbml(dbml_input):
    """Parses DBML text and returns a DataFrame and the schema dictionary."""
    table_pattern = re.compile(r"Table\s+(\w+)\s*\{([^}]+)\}")
    schema = {}
    
    # 1. Parse Schema
    for match in table_pattern.finditer(dbml_input):
        table_name = match.group(1)
        columns_block = match.group(2)
        schema[table_name] = {}
        
        for line in columns_block.strip().split('\n'):
            line = line.strip()
            if not line: continue
            parts = line.split()
            if len(parts) >= 2:
                col_name, col_type = parts[0], parts[1]
                is_pk = 'Yes' if '[pk]' in line.lower() else 'No'
                schema[table_name][col_name] = {'type': col_type, 'is_pk': is_pk}

    # 2. Parse Relationships
    ref_pattern = re.compile(r"Ref:\s*(\w+)\.(\w+)\s*([><-]{1,2})\s*(\w+)\.(\w+)")
    parsed_data = []
    
    for line in dbml_input.splitlines():
        line = line.strip()
        if line.startswith("Ref:"):
            match = ref_pattern.match(line)
            if match:
                table1, col1, operator, table2, col2 = match.groups()
                
                # Map cardinality
                card_map = {">": "Many-to-One (N:1)", "<": "One-to-Many (1:N)", "-": "One-to-One (1:1)", "<>": "Many-to-Many (N:M)"}
                cardinality = card_map.get(operator, "Unknown")
                
                t1_col_info = schema.get(table1, {}).get(col1, {'type': 'Unknown', 'is_pk': 'Unknown'})
                t2_col_info = schema.get(table2, {}).get(col2, {'type': 'Unknown', 'is_pk': 'Unknown'})
                
                parsed_data.append({
                    "Table 1": table1, "Table 1 Column": col1,
                    "Table 2": table2, "Table 2 Column": col2,
                    "Cardinality": cardinality,
                    "Table 1 Column Type": t1_col_info['type'],
                    "Table 2 Column Type": t2_col_info['type'],
                    "Target is PK?": t2_col_info['is_pk']
                })

    df = pd.DataFrame(parsed_data)
    
    if not df.empty:
        df.insert(0, 'Filter 1 (Tables)', df.apply(lambda x: "-".join(sorted([x['Table 1'], x['Table 2']])), axis=1))
        df.insert(1, 'Filter 2 (Columns)', df.apply(lambda x: "-".join(sorted([x['Table 1 Column'], x['Table 2 Column']])), axis=1))
        
    return df, schema

def to_excel_bytes(df):
    """Converts a pandas DataFrame to an Excel file in memory."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Relationships')
        worksheet = writer.sheets['Relationships']
        worksheet.freeze_panes = 'A2'
        worksheet.auto_filter.ref = worksheet.dimensions
        
        from openpyxl.styles import Font
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                if cell.row == 1:
                    cell.font = Font(bold=True)
                try:
                    max_length = max(max_length, len(str(cell.value)))
                except:
                    pass
            worksheet.column_dimensions[column_letter].width = max_length + 2
    return output.getvalue()