import streamlit as st
import pandas as pd
from utils import parse_dbml
import page_extractor
import page_visualizer

def standardize_dataframe(df, t1, t2=None, bridges=None, schema=None):
    """
    Forces the dataframe to flow from the user's first selected table to the second.
    It swaps Table 1 and Table 2, their columns, and their cardinality if they are backward.
    """
    standardized = []
    for _, row in df.iterrows():
        r = row.copy()
        swap = False
        
        if t2 is None:
            # Only 1 table selected: Ensure it is always in the Table 1 column
            if r['Table 2'] == t1:
                swap = True
        else:
            # 2 tables selected
            # Direct: Force flow from t1 to t2
            if r['Table 1'] == t2 and r['Table 2'] == t1:
                swap = True
            # Indirect: Force flow from t1 -> Bridge, and Bridge -> t2
            elif bridges:
                if r['Table 2'] == t1 and r['Table 1'] in bridges:
                    swap = True  # Flips Bridge -> t1 into t1 -> Bridge
                elif r['Table 1'] == t2 and r['Table 2'] in bridges:
                    swap = True  # Flips t2 -> Bridge into Bridge -> t2
                    
        if swap:
            # Swap Tables and Columns
            r['Table 1'], r['Table 2'] = r['Table 2'], r['Table 1']
            r['Table 1 Column'], r['Table 2 Column'] = r['Table 2 Column'], r['Table 1 Column']
            
            # Reverse Cardinality
            if r['Cardinality'] == "One-to-Many (1:N)":
                r['Cardinality'] = "Many-to-One (N:1)"
            elif r['Cardinality'] == "Many-to-One (N:1)":
                r['Cardinality'] = "One-to-Many (1:N)"
            
            # Recalculate PK status for the new target
            if schema:
                t_target = r['Table 2']
                c_target = r['Table 2 Column']
                is_pk = "Yes" if schema.get(t_target, {}).get(c_target, {}).get('is_pk') == 'Yes' else "No"
                r['Target is PK?'] = is_pk

        standardized.append(r)
        
    return pd.DataFrame(standardized) if standardized else pd.DataFrame(columns=df.columns)

# App Config
st.set_page_config(page_title="DBML Extractor & Visualizer", layout="wide")
st.title("🗄️ DBML Relationship Extractor & Visualizer")

# --- 1. Input Section ---
with st.expander("📝 Input DBML Code", expanded=('raw_df' not in st.session_state)):
    dbml_input = st.text_area("Paste your DBML code here:", height=200)
    
    if st.button("Process DBML", type="primary"):
        if not dbml_input.strip():
            st.error("Please paste some DBML code first.")
        else:
            df, schema = parse_dbml(dbml_input)
            if df.empty:
                st.warning("No relationships (`Ref:` lines) were found.")
            else:
                st.session_state['raw_df'] = df
                st.session_state['schema'] = schema
                st.success(f"Successfully extracted {len(df)} relationships!")

# --- 2. Global Filter Panel ---
if 'raw_df' in st.session_state:
    st.divider()
    st.subheader("🔎 Global Filters")
    df = st.session_state['raw_df']
    schema = st.session_state['schema']
    
    all_tables = sorted(set(df['Table 1']).union(set(df['Table 2'])))
    all_columns = sorted(set(df['Table 1 Column']).union(set(df['Table 2 Column'])))
    all_cards = sorted(df['Cardinality'].astype(str).unique())
    all_pk_statuses = sorted(df['Target is PK?'].astype(str).unique())

    col1, col2, col3, col4 = st.columns(4)
    
    show_indirect = False
    intermediate_tables = set()
    
    with col1:
        selected_tables = st.multiselect(
            "Filter by Table (Max 2):", 
            options=all_tables,
            help="Select 1 table to see its relations. Select 2 to see relationships between them."
        )[:2]
        
        if len(selected_tables) == 2:
            show_indirect = st.checkbox("Include 2nd-Level Connections")
            
            if show_indirect:
                t1, t2 = selected_tables[0], selected_tables[1]
                
                # Pre-calculate raw bridge tables
                conn_t1 = set(df[df['Table 1'] == t1]['Table 2']).union(set(df[df['Table 2'] == t1]['Table 1']))
                conn_t2 = set(df[df['Table 1'] == t2]['Table 2']).union(set(df[df['Table 2'] == t2]['Table 1']))
                raw_bridges = conn_t1.intersection(conn_t2)
                
                specific_bridge_placeholder = st.empty()
                default_excl = ["systemuser"] if "systemuser" in all_tables else []
                
                excluded_tables = st.multiselect(
                    "Exclude Bridge Tables:",
                    options=all_tables,
                    default=default_excl,
                    help="ℹ️ Exclude noisy middle tables to prevent irrelevant 2nd-level connections."
                )
                
                available_bridges = raw_bridges - set(excluded_tables)
                
                with specific_bridge_placeholder:
                    specific_bridges = st.multiselect(
                        "Specific Bridge Table(s):",
                        options=sorted(list(available_bridges)),
                        help="ℹ️ Optional: Focus on specific bridging tables."
                    )
                
                intermediate_tables = set(specific_bridges) if specific_bridges else available_bridges
            
    with col2:
        selected_columns = st.multiselect("Filter by Column (Any):", options=all_columns)
    with col3:
        selected_cards = st.multiselect("Filter by Cardinality:", options=all_cards)
    with col4:
        selected_pk = st.multiselect("Filter by Target is PK?:", options=all_pk_statuses)

    # --- Apply Logic ---
    filtered_df = df.copy()
    
    if len(selected_tables) == 1:
        t1 = selected_tables[0]
        filtered_df = filtered_df[(filtered_df['Table 1'] == t1) | (filtered_df['Table 2'] == t1)]
        # Force standardize direction
        filtered_df = standardize_dataframe(filtered_df, t1, schema=schema)
        
    elif len(selected_tables) == 2:
        t1, t2 = selected_tables[0], selected_tables[1]
        
        direct_mask = ((filtered_df['Table 1'] == t1) & (filtered_df['Table 2'] == t2)) | \
                      ((filtered_df['Table 1'] == t2) & (filtered_df['Table 2'] == t1))
        
        if show_indirect and intermediate_tables:
            indirect_mask = (
                ((filtered_df['Table 1'] == t1) & (filtered_df['Table 2'].isin(intermediate_tables))) |
                ((filtered_df['Table 2'] == t1) & (filtered_df['Table 1'].isin(intermediate_tables))) |
                ((filtered_df['Table 1'] == t2) & (filtered_df['Table 2'].isin(intermediate_tables))) |
                ((filtered_df['Table 2'] == t2) & (filtered_df['Table 1'].isin(intermediate_tables)))
            )
            filtered_df = filtered_df[direct_mask | indirect_mask]
        else:
            filtered_df = filtered_df[direct_mask]
            
        # Force standardize direction (t1 -> Bridge -> t2)
        filtered_df = standardize_dataframe(filtered_df, t1, t2, bridges=intermediate_tables, schema=schema)
        
    # Standard filters applied afterward
    if selected_columns:
        filtered_df = filtered_df[filtered_df['Table 1 Column'].isin(selected_columns) | filtered_df['Table 2 Column'].isin(selected_columns)]
    if selected_cards:
        filtered_df = filtered_df[filtered_df['Cardinality'].isin(selected_cards)]
    if selected_pk:
        filtered_df = filtered_df[filtered_df['Target is PK?'].isin(selected_pk)]

    st.divider()
    
    # --- 3. Navigation & Page Routing ---
    page = st.radio(
        "Navigation", 
        ["1. Data Extractor & Export", "2. Relationship Visualizer"], 
        horizontal=True, 
        label_visibility="collapsed"
    )
    
    if page == "1. Data Extractor & Export":
        page_extractor.show(filtered_df, len(df))
    elif page == "2. Relationship Visualizer":
        page_visualizer.show(filtered_df, schema, selected_tables)