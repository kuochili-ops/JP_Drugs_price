import streamlit as st
import pandas as pd
import requests
import io

st.set_page_config(page_title="KEGG 藥物成分日譯英工具", layout="centered")

@st.cache_data(ttl=86400)  # 快取資料 24 小時，避免頻繁請求 API
def get_kegg_mapping():
    url = "https://rest.kegg.jp/list/drug_ja"
    try:
        response = requests.get(url)
        response.raise_for_status()
        mapping = {}
        for line in response.text.strip().split('\n'):
            parts = line.split('\t')
            if len(parts) >= 2:
                names = parts[1].split('; ')
                if len(names) >= 2:
                    jp_name = names[0].strip()
                    en_name = names[1].strip()
                    mapping[jp_name] = en_name
        return mapping
    except Exception as e:
        st.error(f"無法從 KEGG 獲取資料: {e}")
        return {}

st.title("💊 KEGG 藥物日譯英轉換器")
st.write("上傳包含日文成分名的 XLSX 檔，自動對比並新增英文名稱。")

# 1. 獲取對照表
kegg_dict = get_kegg_mapping()

# 2. 上傳檔案
uploaded_file = st.file_uploader("選擇 XLSX 檔案", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.write("### 預覽上傳資料", df.head())
    
    # 讓使用者選擇欄位
    target_col = st.selectbox("請選擇『成分名』所在的欄位：", df.columns)
    
    if st.button("開始轉換"):
        with st.spinner('轉換中...'):
            # 進行對比
            df['英文成分名'] = df[target_col].map(kegg_dict)
            
            # 計算成功率
            match_count = df['英文成分名'].notna().sum()
            st.success(f"轉換完成！成功比對出 {match_count} 筆英文名稱。")
            
            st.write("### 轉換結果預覽", df.head())

            # 準備下載檔案
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            
            st.download_button(
                label="📥 下載處理後的 Excel",
                data=output.getvalue(),
                file_name="translated_drugs.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
