
import streamlit as st
import pandas as pd
from datetime import datetime
import time
import reportlab # Force install for Streamlit Cloud
import altair as alt
from connection import append_data_to_sheet, get_config, read_all_data, update_sheet
from drive_handler import create_folder, upload_to_drive

# ==============================================================================
# 1. CONFIGURATION & CONSTANTS
# ==============================================================================

PAGE_CONFIG = {
    "page_title": "Sistem Laporan Kokurikulum",
    "page_icon": "🏆",
    "layout": "wide"
}

LEVEL_ORDER = [
    "Sekolah", 
    "Daerah", 
    "Bahagian", 
    "Negeri", 
    "Kebangsaan", 
    "Antarabangsa"
]

IDENTITY_OPTIONS = ["Saya Guru", "Saya Ibu Bapa / Penjaga"]
PERINGKAT_OPTIONS = ["Sekolah", "Daerah", "Negeri", "Kebangsaan", "Antarabangsa"]
DATE_COL_NAME = 'Tarikh'
TIMESTAMP_COL = 'Timestamp'

# ==============================================================================
# 2. CORE LOGIC MODULES
# ==============================================================================

def init_app():
    """Initialize page config and load global secrets."""
    st.set_page_config(
        page_title="Sistem Laporan Kokurikulum",
        page_icon="🏫",
        layout="wide"
    )

    # Hide Streamlit Default UI
    st.markdown("""
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        .stDeployButton {display:none;}
        </style>
    """, unsafe_allow_html=True)
    
    config = get_config()
    if not config.get('spreadsheet_id') or not config.get('drive_folder_id'):
        st.error("⚠️ Configuration Error: Missing Sheet ID or Drive Folder ID")
        st.info("Please configure [connections] in .streamlit/secrets.toml")
        st.stop()
        
    return config

def load_and_process_data(spreadsheet_id):
    """Load data from Google Sheets with Smart Date Detection."""
    df = read_all_data(spreadsheet_id)
    
    if df.empty:
        return df
        
    # --- 1. Smart Column Detection ---
    # Try to find 'Tarikh' or similar columns and normalize to standard 'Tarikh'
    target_col = 'Tarikh'
    if target_col not in df.columns:
        # Find candidates (case insensitive)
        candidates = [c for c in df.columns if 'tarikh' in c.lower() or 'date' in c.lower()]
        if candidates:
            # Pick the first one (e.g. 'Tarikh Program' or 'Tarikh ')
            found_col = candidates[0]
            df.rename(columns={found_col: target_col}, inplace=True)
            
    # --- 2. Type Conversion ---
    if target_col in df.columns:
        # Convert to datetime objects first to handle various input formats
        df[target_col] = pd.to_datetime(df[target_col], errors='coerce').dt.date
        
        # --- 3. Force String Logic for Display/Selectbox ---
        # Ensure it's a clean string needed for the Selectbox UI later
        # (Note: For filtering, we might need Date objects. 
        # But user requested "Force String" at the end of load. 
        # However, filter logic uses Date objects. 
        # So providing a string column 'str_Tarikh' might be safer, 
        # OR just ensure we handle types correctly in UI.
        # User Instruction: "ensure Tarikh is string".
        # BUT: line 349: filtered_df[DATE_COL_NAME] >= date_range[0] needs date/datetime objects.
        # IF I force string here, filtering BREAKS.
        # COMPROMISE: Keep as Date object here. Handle String conversion in UI loops.
        # WAIT, User explicitly said: "Force String Conversion: In load_and_process_data last step... df['Tarikh'] = df['Tarikh'].astype(str)..."
        # If I do that, Filter Logic (Step 48 code) will fail.
        # I will Create a dedicated String Column for the UI to use, or fix the filter logic to parse strings.
        # BETTER: Correct the Filter Logic to convert strings back to date if needed, OR keep Date object and convert to string ONLY for Selectbox.
        # The User's instruction "Force String Conversion" might break the DateFilter.
        # Let's look at the instruction again... "ensure Tarikh column is string...".
        # If I do that, I must update the Filter Logic (Line 349) to pd.to_datetime(filtered[..]).dt.date comparison.
        # I will choose to KEEP it as Date for now (for Filter), but ensure the specific UI parts handle it well. 
        # Actually, let's look at current Filter Logic:
        # "if DATE_COL_NAME in filtered.columns: filtered = ... >= date_range[0]"
        # If 'Tarikh' is string '2023-01-01', basic string comparison works ok-ish for ISO dates, but risky.
        #
        # DECISION: I will strictly follow "Smart Detect" and Rename. 
        # I will Apply the "Force String" instruction BUT also update the Filter Logic to handle it safely (convert string back to date for comparison).
        
        # Conversion to string to satisfy User instruction "Step 2"
        df[target_col] = df[target_col].astype(str).replace(['nan', 'NaT', '<NA>'], '')
        
        # Add a helper column for Date Filtering (Actual Date Object)
        df['_date_obj'] = pd.to_datetime(df[target_col], errors='coerce').dt.date

    return df

def compute_analytics(df):
    """Perform aggregations."""
    analytics = {}
    if df.empty: return analytics

    analytics['total_count'] = len(df)
    analytics['unique_students'] = df['Nama Pelajar'].nunique() if 'Nama Pelajar' in df.columns else 0
    if TIMESTAMP_COL in df.columns:
        analytics['latest_entry'] = str(df[TIMESTAMP_COL].max())[:10]
    else:
        analytics['latest_entry'] = "-"

    if 'Peringkat' in df.columns:
        analytics['chart_df'] = df

    if 'Kelas' in df.columns and 'Peringkat' in df.columns:
        pivot_df = pd.crosstab(df['Kelas'], df['Peringkat'])
        existing_extra_cols = [c for c in pivot_df.columns if c not in LEVEL_ORDER]
        final_col_order = [c for c in LEVEL_ORDER] + [c for c in pivot_df.columns if c not in LEVEL_ORDER]
        pivot_df = pivot_df.reindex(columns=final_col_order, fill_value=0)
        analytics['pivot_df'] = pivot_df

    return analytics

def handle_submission(form_data, files, config):
    """Process form submission."""
    spreadsheet_id = config['spreadsheet_id']
    drive_folder_id = config['drive_folder_id']
    
    status = st.status("Sedang memproses laporan...", expanded=True)
    try:
        status.write("⏳ Memproses data...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        display_date = form_data['tarikh'].strftime("%Y-%m-%d")
        
        raw_names = [n.strip() for n in form_data['nama_pelajar'].split('\n') if n.strip()]
        clean_names_str = ", ".join(raw_names)
        folder_suffix = "_".join(raw_names)[:30]
        safe_tajuk = "".join([c for c in form_data['tajuk'] if c.isalnum() or c in (' ', '_', '-')])
        folder_name = f"{timestamp}_{folder_suffix}_{safe_tajuk}"
        
        status.write("📂 Mencipta folder Google Drive...")
        new_folder_id = create_folder(folder_name, drive_folder_id)
        
        status.write("☁️ Memuat naik fail...")
        links = {'surat': '', 'sijil': '', 'g1': '', 'g2': '', 'g3': '', 'g4': ''}
        
        if files['surat']:
            ext = files['surat'].name.split('.')[-1]
            links['surat'] = upload_to_drive(files['surat'], new_folder_id, f"{timestamp}_Surat.{ext}")
        if files['sijil']:
            ext = files['sijil'].name.split('.')[-1]
            links['sijil'] = upload_to_drive(files['sijil'], new_folder_id, f"{timestamp}_Sijil.{ext}")
        for idx, img in enumerate(files['gambar'][:4]):
            ext = img.name.split('.')[-1]
            links[f'g{idx+1}'] = upload_to_drive(img, new_folder_id, f"{timestamp}_Gambar_{idx+1}.{ext}")
            
        status.write("💾 Menyimpan rekod...")
        data_row = [
            timestamp, form_data['identity'], clean_names_str, form_data['kelas'], 
            form_data['tajuk'], form_data['penganjur'], display_date, 
            form_data['tempat'], form_data['peringkat'], form_data['pencapaian'],
            links['surat'], links['sijil'], links['g1'], links['g2'], links['g3'], links['g4']
        ]
        
        append_data_to_sheet(data_row, spreadsheet_id)
        
        status.update(label="✅ Berjaya!", state="complete", expanded=False)
        st.success(f"Laporan berjaya dihantar! Folder: {folder_name}")
        st.balloons()
        
    except Exception as e:
        status.update(label="❌ Gagal", state="error", expanded=True)
        st.error(f"Ralat: {str(e)}")

def handle_data_update(full_df, filtered_scope_df, edited_subset, config):
    """Handle data updates (Admin)."""
    spreadsheet_id = config['spreadsheet_id']
    with st.spinner("Sedang menyegerakan data..."):
        try:
            current_df = full_df.copy()
            current_df.update(edited_subset)
            
            scope_indices = set(filtered_scope_df.index)
            remaining_indices = set(edited_subset.index)
            deleted_indices = scope_indices - remaining_indices
            
            if deleted_indices:
                current_df = current_df.drop(index=list(deleted_indices))
                st.warning(f"Note: {len(deleted_indices)} row(s) deleted.")
                
            if DATE_COL_NAME in current_df.columns:
                current_df[DATE_COL_NAME] = current_df[DATE_COL_NAME].astype(str).replace('NaT', '')
                
            update_sheet(current_df, spreadsheet_id)
            st.success("✅ Data berjaya dikemaskini!")
            time.sleep(1)
            return True
        except Exception as e:
            st.error(f"Ralat semasa menyimpan: {str(e)}")
            return False

# ==============================================================================
# 3. UI RENDERING MODULES
# ==============================================================================

def render_public_submission(config):
    """Render the public submission form."""
    st.header("📝 Isi Borang Laporan")
    st.markdown("---")
    
    with st.form("laporan_form"):
        st.subheader("Maklumat Laporan")
        identity = st.radio("Identiti Pengguna", IDENTITY_OPTIONS)
        
        col1, col2 = st.columns(2)
        with col1:
            nama_pelajar = st.text_area("Nama Pelajar (Satu nama satu baris)", placeholder="Ali bin Abu\nSiti binti Aminah", height=100)
            kelas = st.text_input("Kelas", placeholder="Contoh: 5 Dahlia")
            tarikh = st.date_input("Tarikh Program", datetime.today())
        
        with col2:
            tajuk = st.text_input("Tajuk / Nama Program", placeholder="Contoh: Pertandingan Bola Sepak")
            penganjur = st.text_input("Penganjur", placeholder="Contoh: PPD Petaling Utama")
            tempat = st.text_input("Tempat", placeholder="Contoh: Padang SMK Damansara")
            
        col3, col4 = st.columns(2)
        with col3:
            peringkat = st.selectbox("Peringkat", PERINGKAT_OPTIONS)
        with col4:
            pencapaian = st.text_input("Pencapaian", placeholder="Contoh: Johan / Penyertaan")
            
        st.markdown("---")
        st.subheader("📂 Muat Naik Dokumen")
        
        file_surat = st.file_uploader("Surat (Optional)", type=['pdf', 'jpg', 'png'])
        file_sijil = st.file_uploader("Sijil (Required)", type=['pdf', 'jpg', 'png'])
        files_gambar = st.file_uploader("Gambar (Max 4)", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)
        
        submitted = st.form_submit_button("Hantar Laporan 🚀", use_container_width=True)
        
    if submitted:
        if not (nama_pelajar and kelas and tajuk and file_sijil):
            st.error("❌ Sila lengkapkan maklumat wajib (Nama, Kelas, Tajuk, Sijil)!")
            return
        if len(files_gambar) > 4:
            st.error("❌ Maksimum 4 keping gambar!")
            return
            
        form_data = {
            'identity': identity, 'nama_pelajar': nama_pelajar, 'kelas': kelas, 
            'tarikh': tarikh, 'tajuk': tajuk, 'penganjur': penganjur, 
            'tempat': tempat, 'peringkat': peringkat, 'pencapaian': pencapaian
        }
        files = {'surat': file_surat, 'sijil': file_sijil, 'gambar': files_gambar}
        handle_submission(form_data, files, config)

def render_public_report_generator(config):
    """Render public PDF generator with search."""
    st.header("📄 Jana Laporan Aktiviti (PDF)")
    st.markdown("Cari nama pelajar untuk memuat turun laporan rasmi.")
    
    # Lazy load only when needed
    try:
        import pdf_generator
    except ImportError:
        st.error("⚠️ Module 'reportlab' is missing. Please contact admin.")
        return

    # Load data
    df = load_and_process_data(config['spreadsheet_id'])
    
    if df.empty:
        st.info("Tiada data rekod dalam sistem.")
        return


        
    # Search Mechanism
    search_query = st.text_input("🔍 Carian Nama / No. KP:", placeholder="Taip nama pelajar...")
    
    if search_query:
        # Filter logic (Case insensitive partial match)
        # Assuming 'Nama Pelajar' is the column
        mask = df['Nama Pelajar'].astype(str).str.contains(search_query, case=False, na=False)
        results = df[mask]
        
        if not results.empty:
            # Create labels
            # Construct meaningful label: "Ali | Bola Sepak MSSD | Johan | 2023-10-15"
            # Fallback for 'Tajuk' if missing -> use 'Peringkat'
            event_col = 'Tajuk' if 'Tajuk' in results.columns else 'Peringkat'
            
            # Sort by Date Descending (Latest first)
            # Use _date_obj for sorting if available
            sort_col = '_date_obj' if '_date_obj' in results.columns else DATE_COL_NAME
            if sort_col in results.columns:
                results = results.sort_values(by=sort_col, ascending=False)

            # Create a Label Column and a Mapping Dictionary
            # We map Label -> DF Index to retrieve the exact row later
            label_map = {}
            display_options = []
            
            for idx, row in results.iterrows():
                # Safe str conversion
                name = str(row.get('Nama Pelajar', '?'))
                rank = str(row.get('Peringkat', '-'))
                achievement = str(row.get('Pencapaian', '-'))
                
                # --- Date Fix Start ---
                # Since we forced string in load_and_process_data, 'Tarikh' is string.
                # But let's be safe.
                raw_date = row.get(DATE_COL_NAME)
                formatted_date = str(raw_date) if raw_date else "Tarikh Tidak Dinyatakan"
                # --- Date Fix End ---
                
                # Requested Format: Nama | Peringkat | Pencapaian | Tarikh
                label = f"{name} | {rank} | {achievement} | {formatted_date}"
                
                # Handle duplicate labels if any (append index to make unique)
                if label in label_map:
                    label = f"{label} (#{idx})"
                
                label_map[label] = idx
                display_options.append(label)
            
            st.success(f"✅ Ditemui {len(results)} aktiviti untuk carian anda.")
            
            # Student Info Card
            student_name = str(results.iloc[0].get('Nama Pelajar', '-'))
            student_class = str(results.iloc[0].get('Kelas', '-'))
            
            with st.container():
                st.markdown("#### 👤 Maklumat Pelajar")
                col_info1, col_info2 = st.columns(2)
                col_info1.metric("Nama Pelajar", student_name)
                col_info2.metric("Kelas", student_class)
                st.divider()
            
            selected_label = st.selectbox(
                "Pilih Aktiviti untuk Dijana:", 
                options=display_options,
                index=None,
                placeholder="-- Sila pilih aktiviti --"
            )
            
            if selected_label:
                # Retrieve row index from map
                original_idx = label_map[selected_label]
                selected_row = results.loc[original_idx]
                
                if st.button("Jana & Muat Turun PDF 📥", type="primary"):
                    with st.spinner("Sedang menjana dokumen..."):
                        try:
                            pdf_bytes = pdf_generator.generate_pdf(selected_row.to_dict())
                            
                            # Clean filename: "Laporan_Ali_BolaSepak_2023.pdf"
                            safe_name = "".join(x for x in str(selected_row['Nama Pelajar'])[:10] if x.isalnum())
                            safe_event = "".join(x for x in str(selected_row.get(event_col, ''))[:10] if x.isalnum())
                            fname = f"Laporan_{safe_name}_{safe_event}.pdf"
                            
                            st.download_button(
                                label="Klik untuk Download PDF",
                                data=pdf_bytes,
                                file_name=fname,
                                mime='application/pdf',
                                type='primary'
                            )
                        except Exception as e:
                            st.error(f"Ralat PDF: {str(e)}")
        else:
            st.warning("Tiada rekod ditemui. Sila cuba ejaan lain.")
    else:
        st.info("Sila masukkan nama untuk memulakan carian.")


def render_admin_dashboard(config):
    """Render the protected admin dashboard."""
    st.header("🛡️ Admin Panel")
    
    password = st.text_input("🔑 Kata Laluan Admin", type="password")
    admin_pass = config.get('admin_password')
    
    if password == admin_pass:
        st.success("Akses Diberikan")
        if st.button("Muat Semula Data"):
            st.rerun()
            
        try:
            df = load_and_process_data(config['spreadsheet_id'])
            if df.empty:
                st.warning("Tiada data.")
                return

            # Filter UI
            with st.expander("🔍 Filter Options", expanded=True):
                col1, col2, col3, col4 = st.columns(4)
                
                # Use _date_obj for Date Filter
                filter_date_col = '_date_obj' if '_date_obj' in df.columns else DATE_COL_NAME
                
                if filter_date_col in df.columns:
                    # Convert to datetime date for selector
                    try:
                        valid_dates = pd.to_datetime(df[filter_date_col], errors='coerce').dropna().dt.date
                        if not valid_dates.empty:
                            min_d = valid_dates.min()
                            max_d = valid_dates.max()
                        else:
                            min_d = datetime.today().date()
                            max_d = datetime.today().date()
                    except:
                        min_d = datetime.today().date()
                        max_d = datetime.today().date()
                        
                    with col1:
                        date_range = st.date_input("Tarikh", (min_d, max_d))
                else: date_range = None
                
                with col2:
                    sel_kelas = st.multiselect("Kelas", sorted(df['Kelas'].dropna().unique()))
                with col3:
                    sel_peringkat = st.multiselect("Peringkat", sorted(df['Peringkat'].dropna().unique()))
                with col4:
                    sel_pencapaian = st.multiselect("Pencapaian", sorted(df['Pencapaian'].dropna().unique()))

            # Filter Logic
            filtered_df = df.copy()
            if date_range and len(date_range)==2 and filter_date_col in filtered_df.columns:
                 # Ensure filter col is datetime-like for comparison
                 filtered_df['__temp_date'] = pd.to_datetime(filtered_df[filter_date_col], errors='coerce').dt.date
                 filtered_df = filtered_df[(filtered_df['__temp_date'] >= date_range[0]) & (filtered_df['__temp_date'] <= date_range[1])]
                 filtered_df.drop(columns=['__temp_date'], inplace=True)
                 
            if sel_kelas: filtered_df = filtered_df[filtered_df['Kelas'].isin(sel_kelas)]
            if sel_peringkat: filtered_df = filtered_df[filtered_df['Peringkat'].isin(sel_peringkat)]
            if sel_pencapaian: filtered_df = filtered_df[filtered_df['Pencapaian'].isin(sel_pencapaian)]

            st.caption(f"Records: {len(filtered_df)}")
            analytics = compute_analytics(filtered_df)

            # Analytics UI
            st.subheader("Analisis Data")
            m1, m2, m3 = st.columns(3)
            m1.metric("Total", analytics.get('total_count', 0))
            m2.metric("Unique Students", analytics.get('unique_students', 0))
            m3.metric("Last Update", analytics.get('latest_entry', '-'))

            c1, c2 = st.columns(2)
            if 'chart_df' in analytics:
                with c1:
                    st.altair_chart(alt.Chart(analytics['chart_df']).mark_bar().encode(
                        x='count()', y=alt.Y('Peringkat', sort='-x')
                    ).properties(height=300), use_container_width=True)
                with c2:
                    st.altair_chart(alt.Chart(analytics['chart_df']).mark_bar().encode(
                        x='Peringkat', y='count()', color='Pencapaian'
                    ).properties(height=300), use_container_width=True)

            # Rumusan
            if 'pivot_df' in analytics:
                st.write("Rumusan Pelibatan")
                st.dataframe(analytics['pivot_df'].style.background_gradient(cmap="Blues", axis=None), use_container_width=True)

            # Data Editor
            st.markdown("---")
            st.subheader("Data Editor (Admin Only)")
            display_df = filtered_df.copy()
            if DATE_COL_NAME in display_df.columns:
                display_df[DATE_COL_NAME] = display_df[DATE_COL_NAME].astype(str)
            
            edited_subset = st.data_editor(display_df, num_rows="dynamic", use_container_width=True)
            
            if st.button("Simpan Perubahan (Save)", type="primary"):
                if handle_data_update(df, filtered_df, edited_subset, config):
                    st.rerun()

        except Exception as e:
            st.error(f"Error: {str(e)}")
            
    elif password:
        st.error("Kata laluan salah.")

# ==============================================================================
# 4. MAIN ENTRY POINT
# ==============================================================================

def main():
    config = init_app()
    
    st.markdown("""
        <div style='text-align: center; background-color: #f0f2f6; padding: 20px; border-radius: 10px; margin-bottom: 25px;'>
            <h1 style='color: #0e1117; margin:0;'>🏫 Sistem Pengurusan Kokurikulum</h1>
            <p style='color: #555; margin:5px;'>Jana Laporan & Sijil Pencapaian Pelajar</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Global Tabs
    tab1, tab2, tab3 = st.tabs(["📝 Isi Borang", "📄 Jana Laporan", "🔐 Admin Login"])
    
    with tab1:
        render_public_submission(config)
        
    with tab2:
        render_public_report_generator(config)
        
    with tab3:
        render_admin_dashboard(config)

if __name__ == "__main__":
    main()
