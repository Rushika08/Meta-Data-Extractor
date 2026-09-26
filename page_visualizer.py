import streamlit as st

def get_arrow_html(cardinality):
    """Returns a nicely formatted, subtle gray arrow."""
    if cardinality == "One-to-Many (1:N)": text = "━━( 1 ➔ N )━━▶"
    elif cardinality == "Many-to-One (N:1)": text = "━━( N ➔ 1 )━━▶"
    elif cardinality == "One-to-One (1:1)": text = "━━( 1 ↔ 1 )━━▶"
    elif cardinality == "Many-to-Many (N:M)": text = "━━( N ↔ M )━━▶"
    else: text = "━━━━▶"
    
    # Subdued gray color, slightly smaller, prevents text wrapping on the arrow
    return f"<span style='color: #9ca3af; font-size: 0.85em; margin: 0 12px; white-space: nowrap;'>{text}</span>"

def format_node(table, column, role="endpoint"):
    """
    Formats the table and column names with distinct typography.
    - Endpoints (Source/Dest) adapt to the theme's default text color.
    - Bridges use a distinct violet color.
    - Table name is smaller; Column name is larger and bold.
    """
    color_css = "color: #8b5cf6;" if role == "bridge" else "color: var(--text-color);"
    
    table_html = f"<span style='font-size: 0.85em; opacity: 0.65;'>{table}</span>"
    col_html = f"<strong style='font-size: 1.15em;'>{column}</strong>"
    
    return f"<span style='{color_css}'>{table_html}<span style='opacity:0.4; margin: 0 2px;'>.</span>{col_html}</span>"

def render_card(html_content, card_type):
    """Wraps the content in a beautiful, theme-adaptive transparent card."""
    if card_type == "direct":
        # Green tint (Emerald 500 at 8% opacity)
        border_color = "#10b981"
        bg_color = "rgba(16, 185, 129, 0.08)"
    else:
        # Blue tint (Blue 500 at 8% opacity)
        border_color = "#3b82f6"
        bg_color = "rgba(59, 130, 246, 0.08)"

    card_html = f"""
    <div style="
        border-left: 4px solid {border_color}; 
        background-color: {bg_color}; 
        padding: 14px 18px; 
        border-radius: 6px; 
        margin-bottom: 12px; 
        display: flex; 
        align-items: center; 
        flex-wrap: wrap;
        font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    ">
        {html_content}
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

def show(filtered_df, schema, selected_tables):
    if filtered_df.empty:
        st.warning("No relationships match the current filters.")
        return

    st.write("### Relationship Cards")
    st.markdown("""
    <div style='font-size: 0.9em; margin-bottom: 20px; opacity: 0.8;'>
        Direct relationships are shown in <span style='color: #10b981; font-weight: bold;'>Green</span>. 
        2nd-level connections are shown in <span style='color: #3b82f6; font-weight: bold;'>Blue</span>, 
        with the bridge table highlighted in <span style='color: #8b5cf6; font-weight: bold;'>Violet</span>.
    </div>
    """, unsafe_allow_html=True)
    
    # If exactly 2 tables are selected, process direct and 2nd-level connections
    if len(selected_tables) == 2:
        tA, tB = selected_tables[0], selected_tables[1]
        
        # 1. Direct Relationships (1st Level)
        direct_mask = (filtered_df['Table 1'] == tA) & (filtered_df['Table 2'] == tB)
        direct_df = filtered_df[direct_mask]
        
        if not direct_df.empty:
            st.markdown("#### Direct Relationships")
            for _, row in direct_df.iterrows():
                nodeA = format_node(row['Table 1'], row['Table 1 Column'], role="endpoint")
                nodeB = format_node(row['Table 2'], row['Table 2 Column'], role="endpoint")
                arrow = get_arrow_html(row['Cardinality'])
                render_card(f"{nodeA}{arrow}{nodeB}", "direct")
                
        # 2. Indirect Relationships (2nd Level)
        indirect_df = filtered_df[~direct_mask]
        bridge_tables = set(indirect_df['Table 1']).union(set(indirect_df['Table 2'])) - {tA, tB}
        
        if bridge_tables:
            st.markdown("#### 2nd-Level Connections (via Bridge Tables)")
            
            for tC in sorted(list(bridge_tables)):
                ac_rows = indirect_df[(indirect_df['Table 1'] == tA) & (indirect_df['Table 2'] == tC)]
                bc_rows = indirect_df[(indirect_df['Table 1'] == tC) & (indirect_df['Table 2'] == tB)]
                
                for _, ac_row in ac_rows.iterrows():
                    for _, bc_row in bc_rows.iterrows():
                        
                        # Format Source (Table A)
                        nodeA = format_node(tA, ac_row['Table 1 Column'], role="endpoint")
                        arrow1 = get_arrow_html(ac_row['Cardinality'])
                        
                        # Format Bridge (Table C)
                        colC1, colC2 = ac_row['Table 2 Column'], bc_row['Table 1 Column']
                        if colC1 == colC2:
                            nodeC = format_node(tC, colC1, role="bridge")
                        else:
                            nodeC = format_node(tC, f"({colC1} & {colC2})", role="bridge")
                            
                        # Format Destination (Table B)
                        arrow2 = get_arrow_html(bc_row['Cardinality'])
                        nodeB = format_node(tB, bc_row['Table 2 Column'], role="endpoint")
                        
                        # Render the continuous chain
                        render_card(f"{nodeA}{arrow1}{nodeC}{arrow2}{nodeB}", "indirect")
                        
    else:
        # If 0 or 1 table is selected, render everything as Direct (Green)
        st.markdown("#### All Relationships")
        for _, row in filtered_df.iterrows():
            nodeA = format_node(row['Table 1'], row['Table 1 Column'], role="endpoint")
            nodeB = format_node(row['Table 2'], row['Table 2 Column'], role="endpoint")
            arrow = get_arrow_html(row['Cardinality'])
            render_card(f"{nodeA}{arrow}{nodeB}", "direct")