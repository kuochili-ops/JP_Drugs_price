import streamlit as st
import pandas as pd
import requests
import io
import re

# 禁用沉浸式翻譯插件可能導致的 UI 錯誤
st.markdown("""
    <style>
    .stApp {
        overflow: auto;
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=86400)
def get_kegg_mapping():
    url = "https://rest.kegg.jp/list/drug_ja"
    try:
        response = requests.get(url)
        response.raise_for_status()
        mapping_list = []
        for line in response.text.strip().split('\n'):
            parts = line.split('\t')
            if len(parts) >= 2:
                # 取得日文名與英文名
                names = parts[1].split('; ')
                if len(names) >= 2:
                    raw_jp = names[0].strip()
                    # 清理 API 的日文名：移除括號內容 (例如: (JP18) -> "")
                    clean_jp = re.sub(r'[\(（].*?[\)）]', '', raw_jp).strip()
                    
                    mapping_list.append({
                        'clean_jp': clean_jp,
                        'en': names[1].strip()
                    })
        # 按照長度排序，先比對長的字串，防止誤判
        return sorted(mapping_list, key=lambda x: len(x['clean_jp']), reverse=True)
    except Exception as e:
        st.error(f"API 連線異常: {e}")
        return []

def find_match(cell_value, mapping_list):
    if pd.isna(cell_value): return None
    
    # 預處理 Excel 儲存格：移除所有全角/半角空格
    target = str(cell_value).replace(' ', '').replace('　', '')
    
    # 優先嘗試「完整包含」比對
    for item in mapping_list:
        if item['clean_jp'] and item['clean_jp'] in target:
            return item['en']
            
    return "無匹配結果"

# --- Streamlit UI ---
st.title("💊 藥物日譯英轉換工具")
mapping_list = get_kegg_mapping()

uploaded_file = st.file_uploader("上傳 Excel 或 CSV", type=["xlsx", "csv"])

if uploaded_file:
    df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
    target_col = st.selectbox("請選擇『成分名』欄位", df.columns)
    
    if st.button("執行轉換"):
        with st.spinner('比對中...'):
            df['英文成分名'] = df[target_col].apply(lambda x: find_match(x, mapping_list))
            st.dataframe(df)
            
            # 檔案下載邏輯
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            st.download_button("📥 下載結果", output.getvalue(), "translated.xlsx")
