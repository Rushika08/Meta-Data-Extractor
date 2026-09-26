import streamlit as st

def get_arrow(cardinality):
    """Returns a nicely formatted arrow string showing the cardinality direction."""
    if cardinality == "One-to-Many (1:N)":
        return "━━( 1 ➔ N )━━▶"
    elif cardinality == "Many-to-One (N:1)":
        return "━━( N ➔ 1 )━━▶"
    elif cardinality == "One-to-One (1:1)":
        return "━━( 1 ↔ 1 )━━▶"
    elif cardinality == "Many-to-Many (N:M)":
        return "━━( N ↔ M )━━▶"
    else:
        return "━━━━▶"

def format_rel(row):
    """Formats a single row into standard Streamlit Markdown."""
    t1, c1 = row['Table 1'], row['Table 1 Column']
    t2, c2 = row['Table 2'], row['Table 2 Column']
    arrow = get_arrow(row['Cardinality'])
    
    # We use native Markdown bolding and code blocks for perfect theme compatibility
    return f"**{t1}**.`{c1}` &nbsp; {arrow} &nbsp; **{t2}**.`{c2}`"

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
                # Native Green Alert Box
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
                
                # Pair every A->C link with every C->B link
                for _, ac_row in ac_rows.iterrows():
                    for _, bc_row in bc_rows.iterrows():
                        c1_str = format_rel(ac_row)
                        c2_str = format_rel(bc_row)
                        
                        # Native Blue Alert Box (the two spaces before \n force a line break in Markdown)
                        st.info(f"{c1_str}  \n{c2_str}")
                        
    else:
        # If the user selected 0 or 1 table, render everything as 1st Level (Green)
        st.markdown("#### All Relationships")
        for _, row in filtered_df.iterrows():
            # Native Green Alert Box
            st.success(format_rel(row))