import streamlit as st
from utils import to_excel_bytes

def show(filtered_df, total_rows):
    st.write(f"**Showing {len(filtered_df)} of {total_rows} relationships:**")
    
    # Drop the filter columns just for the Streamlit display
    display_df = filtered_df.drop(columns=['Filter 1 (Tables)', 'Filter 2 (Columns)'], errors='ignore')
    
    # Styling function to shade Table 1 (1st column) and Table 2 (3rd column)
    def style_dataframe(df):
        target_cols = ['Table 1', 'Table 2']
        def color_cols(col):
            if col.name in target_cols:
                # Soft, theme-adaptive shading (works seamlessly in both Light and Dark mode)
                return ['background-color: rgba(59, 130, 246, 0.08);'] * len(col)
            return [''] * len(col)
        return df.style.apply(color_cols, axis=0)

    # Display the styled interactive table
    st.dataframe(style_dataframe(display_df), use_container_width=True, hide_index=True)
    
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