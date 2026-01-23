import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="多來源藥價查詢系統", layout="wide")

@st.cache_data
def load_combined_data():
    """載入並整合目錄下的四個 XLSX 檔案"""
    # 定義檔案名稱與對應的標籤
    file_config = {
        "齒科": "medical_translation_final (齒科).xlsx",
        "外用": "medical_translation_final (外用).xlsx",
        "內用": "medical_translation_final (內用).xlsx",
        "注射": "medical_translation_final(注射).xlsx"
    }
    
    combined_list = []
    
    for source_label, file_name in file_config.items():
        if os.path.exists(file_name):
            try:
                # 讀取 Excel 檔案
                df = pd.read_excel(file_name)
                
                # 篩選必要欄位，避免欄位名稱微差導致錯誤
                # 假設欄位名稱為：成分名, 英文成分名, 規格, 薬価
                df = df[['成分名', '英文成分名', '規格', '薬価']].copy()
                
                # 新增資料來源標籤
                df['來源'] = source_label
                
                # 清洗藥價數據：確保為數值，處理可能的空值
                df['薬価'] = pd.to_numeric(df['薬価'], errors='coerce')
                
                combined_list.append(df)
            except Exception as e:
                st.error(f"讀取 {file_name} 時發生錯誤: {e}")
        else:
            st.warning(f"提醒：未在目錄下找到檔案 {file_name}")
            
    if not combined_list:
        return pd.DataFrame()
        
    return pd.concat(combined_list, ignore_index=True)

# 載入資料庫
df_db = load_combined_data()

st.title("🔍 聯合藥價查詢系統")
st.markdown("輸入 **日文成分名** 或 **英文成分名**，系統將自動比對 **齒科、外用、內用、注射** 四大來源之價格。")

# 搜尋列
query = st.text_input("輸入搜尋關鍵字（例如：リドカイン 或 Lidocaine）", "").strip().lower()

if query:
    # 模糊搜尋日文與英文欄位
    mask = (
        df_db['成分名'].str.contains(query, case=False, na=False) | 
        df_db['英文成分名'].str.contains(query, case=False, na=False)
    )
    search_results = df_db[mask]

    if not search_results.empty:
        # 依照「成分名」與「規格」分組，統計藥價與來源
        # 同規格不同價者，統計其 Min 與 Max
        summary = search_results.groupby(['成分名', '英文成分名', '規格']).agg({
            '薬価': ['min', 'max'],
            '來源': lambda x: ', '.join(sorted(x.unique()))
        }).reset_index()

        # 重新命名欄位
        summary.columns = ['成分名', '英文成分名', '規格', '最低藥價', '最高藥價', '來源標示']

        # 處理藥價顯示邏輯
        def format_price_range(row):
            p_min = row['最低藥價']
            p_max = row['最高藥價']
            if pd.isna(p_min): return "無資料"
            if p_min == p_max:
                return f"{p_min:,.1f}"
            else:
                return f"{p_min:,.1f} ～ {p_max:,.1f}"

        summary['藥價 (JPY)'] = summary.apply(format_price_range, axis=1)

        # 顯示最終報表
        st.subheader(f"找到 {len(summary)} 項符合規格的結果")
        st.table(summary[['成分名', '英文成分名', '規格', '藥價 (JPY)', '來源標示']])
        
        # 顯示詳細原始清單（包含品名與廠商）
        with st.expander("查看原始詳細資料（含所有收錄品項）"):
            st.dataframe(search_results.sort_values(by='薬価'))
    else:
        st.error("查無資料，請嘗試其他關鍵字。")

else:
    st.info("請輸入成分名稱進行查詢。")

# 統計側邊欄
if not df_db.empty:
    st.sidebar.header("資料庫統計")
    st.sidebar.write(f"總品項數：{len(df_db)}")
    for src in ["齒科", "外用", "內用", "注射"]:
        count = len(df_db[df_db['來源'] == src])
        st.sidebar.text(f"· {src}: {count} 筆")
