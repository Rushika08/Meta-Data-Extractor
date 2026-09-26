import streamlit as st
from utils import to_excel_bytes

def show(filtered_df, total_rows):
    st.write(f"**Showing {len(filtered_df)} of {total_rows} relationships:**")
    
    # Drop the filter columns just for the Streamlit display
    display_df = filtered_df.drop(columns=['Filter 1 (Tables)', 'Filter 2 (Columns)'], errors='ignore')
    
    # Display the cleaner interactive table
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    st.subheader("📥 Export")
    st.write("Download the current table (including your active filters) to Excel.")
    
    # Pass the FULL filtered_df to Excel so the filter columns are still included in the download
    excel_data = to_excel_bytes(filtered_df)
    st.download_button(
        label="Download Filtered Excel File",
        data=excel_data,
        file_name="Filtered_Database_Relationships.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )