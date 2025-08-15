#!/usr/bin/env python3
"""
Streamlit UI for Index Data URL Management
Web interface for managing CSV URL configurations and running data loads
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import json
from url_manager import URLManager
from generic_data_loader import GenericIndexDataLoader
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Index Data URL Manager",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'url_manager' not in st.session_state:
    st.session_state.url_manager = URLManager()
    st.session_state.url_manager.connect_to_mongodb()

if 'data_loader' not in st.session_state:
    st.session_state.data_loader = GenericIndexDataLoader()

def display_url_statistics():
    """Display URL statistics in sidebar"""
    stats = st.session_state.url_manager.get_statistics()
    
    if stats:
        st.sidebar.markdown("### 📊 Statistics")
        st.sidebar.metric("Total URLs", stats.get('total_urls', 0))
        st.sidebar.metric("Active URLs", stats.get('active_urls', 0))
        st.sidebar.metric("Valid URLs", stats.get('valid_urls', 0))
        st.sidebar.metric("Unique Indices", stats.get('unique_indices', 0))
        
        if stats.get('index_names'):
            st.sidebar.markdown("**Index Names:**")
            for name in stats['index_names']:
                st.sidebar.write(f"• {name}")

def add_url_form():
    """Form for adding new URLs"""
    st.header("➕ Add New URL")
    
    with st.form("add_url_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            url = st.text_input(
                "CSV URL *", 
                placeholder="https://example.com/data.csv",
                help="URL to download CSV data from"
            )
            
            index_name = st.text_input(
                "Index Name", 
                placeholder="Leave empty to auto-extract from URL",
                help="Name of the index (e.g., NIFTY 50, SENSEX)"
            )
            
        with col2:
            description = st.text_area(
                "Description", 
                placeholder="Brief description of this data source",
                height=100
            )
            
            tags_input = st.text_input(
                "Tags", 
                placeholder="equity, large-cap, nifty (comma-separated)",
                help="Tags for categorization"
            )
            
        is_active = st.checkbox("Active", value=True, help="Whether this URL should be processed during bulk operations")
        
        submitted = st.form_submit_button("Add URL", type="primary")
        
        if submitted:
            if not url:
                st.error("URL is required!")
                return
            
            # Parse tags
            tags = [tag.strip() for tag in tags_input.split(',') if tag.strip()] if tags_input else []
            
            # Add URL
            success, message = st.session_state.url_manager.add_url(
                url=url,
                index_name=index_name if index_name else None,
                description=description,
                tags=tags,
                is_active=is_active
            )
            
            if success:
                st.success(f"✅ URL added successfully! ID: {message}")
                st.rerun()
            else:
                st.error(f"❌ Failed to add URL: {message}")

def display_urls():
    """Display and manage existing URLs"""
    st.header("📋 Manage URLs")
    
    # Get all URLs
    urls = st.session_state.url_manager.get_all_urls()
    
    if not urls:
        st.info("No URLs configured yet. Add your first URL using the form above.")
        return
    
    # Convert to DataFrame for display
    df_data = []
    for url in urls:
        df_data.append({
            'ID': url['_id'],
            'Index Name': url['index_name'],
            'URL': url['url'][:50] + '...' if len(url['url']) > 50 else url['url'],
            'Active': '✅' if url['is_active'] else '❌',
            'Valid': '✅' if url.get('is_valid', False) else '❌',
            'Downloads': url.get('download_count', 0),
            'Last Downloaded': url.get('last_downloaded', 'Never'),
            'Created': url['created_at'].strftime('%Y-%m-%d') if url['created_at'] else 'Unknown'
        })
    
    df = pd.DataFrame(df_data)
    
    # Display dataframe
    st.dataframe(df, use_container_width=True)
    
    # Action buttons
    st.subheader("🎯 Actions")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🔄 Process All Active", type="primary"):
            process_all_urls()
    
    with col2:
        if st.button("📊 Refresh Data"):
            st.rerun()
    
    with col3:
        selected_ids = st.multiselect(
            "Select URLs to process",
            options=[url['_id'] for url in urls],
            format_func=lambda x: next((url['index_name'] for url in urls if url['_id'] == x), x)
        )
        
        if selected_ids and st.button("▶️ Process Selected"):
            process_selected_urls(selected_ids)
    
    with col4:
        # Download current URL list as JSON
        if st.button("💾 Export URLs"):
            urls_json = json.dumps(urls, indent=2, default=str)
            st.download_button(
                label="Download URLs JSON",
                data=urls_json,
                file_name=f"url_configs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    
    # Detailed URL management
    st.subheader("🔧 URL Details & Management")
    
    if urls:
        selected_url_id = st.selectbox(
            "Select URL to manage",
            options=[url['_id'] for url in urls],
            format_func=lambda x: next((f"{url['index_name']} - {url['url'][:50]}..." for url in urls if url['_id'] == x), x)
        )
        
        if selected_url_id:
            display_url_details(selected_url_id, urls)

def display_url_details(url_id, urls):
    """Display detailed information for a specific URL"""
    url_config = next((url for url in urls if url['_id'] == url_id), None)
    
    if not url_config:
        st.error("URL not found!")
        return
    
    # Display details in expandable section
    with st.expander("📄 URL Details", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Index Name:**", url_config['index_name'])
            st.write("**URL:**", url_config['url'])
            st.write("**Active:**", "Yes" if url_config['is_active'] else "No")
            st.write("**Valid:**", "Yes" if url_config.get('is_valid', False) else "No")
            
        with col2:
            st.write("**Description:**", url_config.get('description', 'N/A'))
            st.write("**Tags:**", ', '.join(url_config.get('tags', [])) if url_config.get('tags') else 'None')
            st.write("**Downloads:**", url_config.get('download_count', 0))
            st.write("**Created:**", url_config['created_at'].strftime('%Y-%m-%d %H:%M:%S') if url_config['created_at'] else 'Unknown')
        
        if url_config.get('last_downloaded'):
            st.write("**Last Downloaded:**", url_config['last_downloaded'].strftime('%Y-%m-%d %H:%M:%S'))
        
        if url_config.get('last_error'):
            st.error(f"**Last Error:** {url_config['last_error']}")
        
        if url_config.get('validation_message'):
            if url_config.get('is_valid'):
                st.success(f"**Validation:** {url_config['validation_message']}")
            else:
                st.warning(f"**Validation:** {url_config['validation_message']}")
    
    # Edit form
    with st.expander("✏️ Edit URL"):
        with st.form(f"edit_url_{url_id}"):
            new_url = st.text_input("URL", value=url_config['url'])
            new_index_name = st.text_input("Index Name", value=url_config['index_name'])
            new_description = st.text_area("Description", value=url_config.get('description', ''))
            new_tags = st.text_input("Tags", value=', '.join(url_config.get('tags', [])))
            new_is_active = st.checkbox("Active", value=url_config['is_active'])
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("💾 Update URL", type="primary"):
                    update_url(url_id, new_url, new_index_name, new_description, new_tags, new_is_active)
            
            with col2:
                if st.form_submit_button("🗑️ Delete URL", type="secondary"):
                    delete_url(url_id)

def update_url(url_id, url, index_name, description, tags, is_active):
    """Update URL configuration"""
    tags_list = [tag.strip() for tag in tags.split(',') if tag.strip()] if tags else []
    
    success, message = st.session_state.url_manager.update_url(
        url_id,
        url=url,
        index_name=index_name,
        description=description,
        tags=tags_list,
        is_active=is_active
    )
    
    if success:
        st.success("✅ URL updated successfully!")
        time.sleep(1)
        st.rerun()
    else:
        st.error(f"❌ Failed to update URL: {message}")

def delete_url(url_id):
    """Delete URL configuration"""
    success, message = st.session_state.url_manager.delete_url(url_id)
    
    if success:
        st.success("✅ URL deleted successfully!")
        time.sleep(1)
        st.rerun()
    else:
        st.error(f"❌ Failed to delete URL: {message}")

def process_all_urls():
    """Process all active URLs"""
    with st.spinner("Processing all active URLs..."):
        try:
            st.session_state.data_loader.connect_to_mongodb()
            success = st.session_state.data_loader.process_all_active_urls()
            
            if success:
                st.success("✅ All active URLs processed successfully!")
                
                # Show stats
                stats = st.session_state.data_loader.get_collection_stats()
                if stats:
                    st.write("**Data Statistics:**")
                    st.write(f"Total documents: {stats['total_documents']}")
                    
                    if stats['index_stats']:
                        for stat in stats['index_stats']:
                            st.write(f"• {stat['_id']}: {stat['count']} documents")
            else:
                st.error("❌ Failed to process URLs. Check logs for details.")
                
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
        finally:
            st.session_state.data_loader.close_connection()

def process_selected_urls(url_ids):
    """Process selected URLs"""
    with st.spinner(f"Processing {len(url_ids)} selected URLs..."):
        try:
            st.session_state.data_loader.connect_to_mongodb()
            success = st.session_state.data_loader.process_specific_urls(url_ids)
            
            if success:
                st.success(f"✅ {len(url_ids)} URLs processed successfully!")
                
                # Show stats
                stats = st.session_state.data_loader.get_collection_stats()
                if stats and stats['index_stats']:
                    st.write("**Updated Data:**")
                    for stat in stats['index_stats']:
                        st.write(f"• {stat['_id']}: {stat['count']} documents")
            else:
                st.error("❌ Failed to process selected URLs. Check logs for details.")
                
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
        finally:
            st.session_state.data_loader.close_connection()

def display_data_overview():
    """Display overview of loaded data"""
    st.header("📊 Data Overview")
    
    try:
        # Connect and get stats
        st.session_state.data_loader.connect_to_mongodb()
        stats = st.session_state.data_loader.get_collection_stats()
        
        if not stats or stats['total_documents'] == 0:
            st.info("No data loaded yet. Configure URLs and run data loading to see results here.")
            return
        
        # Display metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Documents", stats['total_documents'])
        
        with col2:
            st.metric("Number of Indices", len(stats['index_stats']))
        
        with col3:
            latest_update = max([stat['last_update'] for stat in stats['index_stats']] + [datetime.min])
            st.metric("Latest Update", latest_update.strftime('%Y-%m-%d %H:%M') if latest_update != datetime.min else 'Never')
        
        # Display index statistics
        if stats['index_stats']:
            st.subheader("📈 Index Statistics")
            
            index_df = pd.DataFrame(stats['index_stats'])
            index_df.columns = ['Index Name', 'Document Count', 'Last Update']
            index_df['Last Update'] = pd.to_datetime(index_df['Last Update']).dt.strftime('%Y-%m-%d %H:%M:%S')
            
            st.dataframe(index_df, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error loading data overview: {str(e)}")
    finally:
        st.session_state.data_loader.close_connection()

def main():
    """Main Streamlit app"""
    st.title("📊 Index Data URL Manager")
    st.markdown("Manage CSV data sources for index constituents and market data")
    
    # Sidebar
    st.sidebar.title("Navigation")
    display_url_statistics()
    
    # Main tabs
    tab1, tab2, tab3 = st.tabs(["🔗 URL Management", "📊 Data Overview", "📖 Help"])
    
    with tab1:
        add_url_form()
        st.divider()
        display_urls()
    
    with tab2:
        display_data_overview()
    
    with tab3:
        st.markdown("""
        ## 📖 Help & Usage Guide
        
        ### Adding URLs
        1. **URL**: Enter the direct CSV download URL or a page containing CSV download links
        2. **Index Name**: Specify the index name (e.g., "NIFTY 50") or leave empty for auto-extraction
        3. **Description**: Brief description of the data source
        4. **Tags**: Comma-separated tags for categorization
        5. **Active**: Check to include in bulk processing operations
        
        ### Processing Data
        - **Process All Active**: Downloads and loads data from all active URLs
        - **Process Selected**: Downloads and loads data from specific URLs
        - Data is stored in MongoDB collection `index_meta`
        - Existing data for each index is replaced during updates
        
        ### URL Management
        - View all configured URLs with status indicators
        - Edit URL details including activation status
        - Delete unwanted URL configurations
        - Export URL configurations as JSON
        
        ### Data Overview
        - View statistics about loaded data
        - See document counts per index
        - Check last update timestamps
        
        ### Auto Index Name Extraction
        The system can automatically extract index names from URLs:
        - `nifty50` → "NIFTY 50"
        - `sensex30` → "SENSEX 30" 
        - `bse500` → "BSE 500"
        - And many other patterns
        """)

if __name__ == "__main__":
    main()
