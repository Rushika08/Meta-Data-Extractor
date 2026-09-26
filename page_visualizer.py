import streamlit as st

def get_directed_details(row, from_table, to_table):
    """
    Analyzes a relationship and returns the origin column, arrow, and target column.
    Automatically reverses the cardinality arrow if the flow needs to go backwards 
    to maintain a left-to-right visual chain.
    """
    if row['Table 1'] == from_table:
        c_from = row['Table 1 Column']
        c_to = row['Table 2 Column']
        card = row['Cardinality']
    else:
        c_from = row['Table 2 Column']
        c_to = row['Table 1 Column']
        
        # Reverse the cardinality visually for a left-to-right flow
        if row['Cardinality'] == "One-to-Many (1:N)":
            card = "Many-to-One (N:1)"
        elif row['Cardinality'] == "Many-to-One (N:1)":
            card = "One-to-Many (1:N)"
        else:
            card = row['Cardinality']
    
    # Generate the exact arrow string
    if card == "One-to-Many (1:N)":
        arrow = "━━( 1 ➔ N )━━▶"
    elif card == "Many-to-One (N:1)":
        arrow = "━━( N ➔ 1 )━━▶"
    elif card == "One-to-One (1:1)":
        arrow = "━━( 1 ↔ 1 )━━▶"
    elif card == "Many-to-Many (N:M)":
        arrow = "━━( N ↔ M )━━▶"
    else:
        arrow = "━━━━▶"
        
    return c_from, arrow, c_to

def format_rel(row):
    """Formats a standard 1st-level direct relationship."""
    c_from, arrow, c_to = get_directed_details(row, row['Table 1'], row['Table 2'])
    return f"**{row['Table 1']}**.`{c_from}` &nbsp; {arrow} &nbsp; **{row['Table 2']}**.`{c_to}`"

def show(filtered_df, schema, selected_tables):
    if filtered_df.empty:
        st.warning("No relationships match the current filters.")
        return

    st.write("### Relationship Cards")
    st.write("Direct relationships are shown in **Green**. 2nd-level bridge connections are shown in **Blue**.")
    
    # If exactly 2 tables are selected, we can split them into 1st-level and 2nd-level
    if len(selected_tables) == 2:
        tA, tB = selected_tables[0], selected_tables[1]
        
        # 1. Direct Relationships (1st Level)
        direct_mask = ((filtered_df['Table 1'] == tA) & (filtered_df['Table 2'] == tB)) | \
                      ((filtered_df['Table 1'] == tB) & (filtered_df['Table 2'] == tA))
        
        direct_df = filtered_df[direct_mask]
        
        if not direct_df.empty:
            st.markdown("#### Direct Relationships")
            for _, row in direct_df.iterrows():
                st.success(format_rel(row))
                
        # 2. Indirect Relationships (2nd Level)
        indirect_df = filtered_df[~direct_mask]
        # Identify the intermediate tables that are NOT the two we searched for
        bridge_tables = set(indirect_df['Table 1']).union(set(indirect_df['Table 2'])) - {tA, tB}
        
        if bridge_tables:
            st.markdown("#### 2nd-Level Connections (via Bridge Tables)")
            
            for tC in sorted(list(bridge_tables)):
                # Find all rows linking Table A to Bridge Table C
                ac_mask = ((indirect_df['Table 1'] == tA) & (indirect_df['Table 2'] == tC)) | \
                          ((indirect_df['Table 1'] == tC) & (indirect_df['Table 2'] == tA))
                ac_rows = indirect_df[ac_mask]
                
                # Find all rows linking Table B to Bridge Table C
                bc_mask = ((indirect_df['Table 1'] == tB) & (indirect_df['Table 2'] == tC)) | \
                          ((indirect_df['Table 1'] == tC) & (indirect_df['Table 2'] == tB))
                bc_rows = indirect_df[bc_mask]
                
                # Pair every A->C link with every C->B link to build the chain
                for _, ac_row in ac_rows.iterrows():
                    for _, bc_row in bc_rows.iterrows():
                        
                        # Get the flow from Table A -> Bridge Table C
                        colA, arrow1, colC1 = get_directed_details(ac_row, tA, tC)
                        # Get the flow from Bridge Table C -> Table B
                        colC2, arrow2, colB = get_directed_details(bc_row, tC, tB)
                        
                        # If the bridge uses the exact same column for both links, merge them.
                        # Otherwise, display both columns in the middle.
                        if colC1 == colC2:
                            bridge_str = f"**{tC}**.`{colC1}`"
                        else:
                            bridge_str = f"**{tC}**.(`{colC1}` & `{colC2}`)"
                            
                        # Build the final continuous string
                        chain_str = f"**{tA}**.`{colA}` &nbsp; {arrow1} &nbsp; {bridge_str} &nbsp; {arrow2} &nbsp; **{tB}**.`{colB}`"
                        
                        st.info(chain_str)
                        
    else:
        # If the user selected 0 or 1 table, render everything as 1st Level (Green)
        st.markdown("#### All Relationships")
        for _, row in filtered_df.iterrows():
            st.success(format_rel(row))