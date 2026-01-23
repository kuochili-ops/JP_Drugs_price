import streamlit as st
import pandas as pd
import os

# 設定網頁配置
st.set_page_config(page_title="2025 藥價聯合查詢系統", layout="wide")

# --- 彈出說明視窗內容 ---
@st.dialog("系統使用說明與簡介")
def show_help():
    st.markdown("""
    ### 🌟 系統簡介
    本系統整合日本厚生勞動省 (MHLW) **2025 年 4 月**最新發布的藥價基準資料，結合 **KEGG 醫學資料庫** 與 **Azure AI 翻譯** 技術，提供跨類別的藥價檢索服務。

    ### 🚀 核心用途
    1. **藥價範圍檢索**：自動聚合「同成分、同規格」藥品，顯示市場最低與最高藥價。
    2. **跨劑型對比**：一次搜尋即可查看該成分在「內服、外用、注射、齒科」類別的價格分布。
    3. **專業醫學翻譯**：提供精確的日、英成分對照。

    ### 📖 使用說明
    * **搜尋方式**：在搜尋框輸入日文（如：`アスピリン`）或英文（如：`Aspirin`）。
    * **藥價顯示**：若規格存在多個廠牌，顯示為 `¥最低 ～ ¥最高`。
    * **來源標註**：標註該資訊來自齒科、內用、外用或注射類別。
    * **詳細資料**：點擊「查看原始詳情」可看到生產廠商與完整品名。
    
    ---
    *資料來源：[日本厚生勞動省 令和7年4月藥價基準](https://www.mhlw.go.jp/topics/2025/04/tp20250401-01.html)*
    """)

# --- 資料載入邏輯 (保持不變) ---
@st.cache_data
def load_and_combine_data():
    file_map = {
        "齒科": "medical_translation_final (齒科).xlsx",
        "外用": "medical_translation_final (外用).xlsx",
        "內用": "medical_translation_final (內用).xlsx",
        "注射": "medical_translation_final(注射).xlsx"
    }
    combined_list = []
    for source_label, file_name in file_map.items():
        if os.path.exists(file_name):
            try:
                df = pd.read_excel(file_name)
                cols = ['成分名', '英文成分名', '規格', '薬価']
                df = df[cols].copy()
                df['來源類型'] = source_label
                df['薬価'] = pd.to_numeric(df['薬価'], errors='coerce')
                combined_list.append(df)
            except Exception: pass
    return pd.concat(combined_list, ignore_index=True) if combined_list else pd.DataFrame()

db = load_and_combine_data()

# --- 主介面 ---
col_title, col_help = st.columns([8, 2])

with col_title:
    st.title("🔍 2025 年度藥價聯合查詢系統")

with col_help:
    st.write("") # 調整對齊
    if st.button("❓ 使用說明"):
        show_help()

st.caption("優先顯示同成分、同規格之藥價區間 (最低~最高)")

# --- 搜尋邏輯 ---
search_input = st.text_input("請輸入成分名稱（日文或英文）：", placeholder="例如：Lidocaine 或 リドカイン").strip().lower()

if search_input:
    mask = (db['成分名'].str.contains(search_input, case=False, na=False) | 
            db['英文成分名'].str.contains(search_input, case=False, na=False))
    res = db[mask]

    if not res.empty:
        summary = res.groupby(['成分名', '英文成分名', '規格']).agg({
            '薬価': ['min', 'max'],
            '來源類型': lambda x: '、'.join(sorted(x.unique()))
        }).reset_index()
        summary.columns = ['成分名', '英文成分名', '規格', 'Min', 'Max', '資料來源']
        
        summary['藥價 (JPY)'] = summary.apply(
            lambda r: f"¥{r['Min']:,.2f}" if r['Min'] == r['Max'] else f"¥{r['Min']:,.2f} ～ ¥{r['Max']:,.2f}", axis=1
        )
        
        st.table(summary[['成分名', '英文成分名', '規格', '藥價 (JPY)', '資料來源']])
        
        with st.expander("查看原始品項詳情"):
            st.dataframe(res)
    else:
        st.warning("查無符合成分。")
