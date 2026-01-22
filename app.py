import streamlit as st
import pandas as pd
import requests
import io
import re

st.set_page_config(page_title="KEGG 藥物比對工具", layout="wide")

@st.cache_data(ttl=86400)
def get_kegg_mapping():
    url = "https://rest.kegg.jp/list/drug_ja"
    try:
        response = requests.get(url)
        response.encoding = 'utf-8' # 強制使用 utf-8 處理漢字
        mapping_list = []
        for line in response.text.strip().split('\n'):
            parts = line.split('\t')
            if len(parts) >= 2:
                names = parts[1].split('; ')
                if len(names) >= 2:
                    raw_jp = names[0].strip()
                    # 移除所有類型的括號及其內容，避免 "(JP18)" 影響比對
                    clean_jp = re.sub(r'[\(（].*?[\)）]', '', raw_jp).strip()
                    if clean_jp:
                        mapping_list.append({
                            'clean_jp': clean_jp,
                            'en': names[1].strip()
                        })
        # 按照字串長度排序 (由長到短)，這對漢字比對至關重要
        return sorted(mapping_list, key=lambda x: len(x['clean_jp']), reverse=True)
    except Exception as e:
        st.error(f"KEGG 連線異常: {e}")
        return []

def find_match(cell_value, mapping_list):
    if pd.isna(cell_value): return None
    
    # 1. 清理 Excel 儲存格字串：移除空白、換行
    target = str(cell_value).replace(' ', '').replace('　', '').strip()
    
    # 2. 進行包含比對
    for item in mapping_list:
        # 如果 API 的 clean_jp (例如: ドロペリドール) 在 Excel 格子裡 (例如: ドロペリドール注)
        if item['clean_jp'] in target:
            return item['en']
    
    return None

st.title("💊 藥物日譯英轉換器 (漢字強化版)")

mapping_list = get_kegg_mapping()

# 提供除錯資訊：查看 API 抓到了多少筆
if mapping_list:
    st.sidebar.success(f"目前對照表共有 {len(mapping_list)} 筆成分")

uploaded_file = st.file_uploader("上傳檔案 (XLSX 或 CSV)", type=["xlsx", "csv"])

if uploaded_file:
    # 處理 CSV 編碼，防止漢字亂碼
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, encoding='utf-8')
        else:
            df = pd.read_excel(uploaded_file)
    except UnicodeDecodeError:
        df = pd.read_csv(uploaded_file, encoding='shift-jis')

    target_col = st.selectbox("選擇包含『成分名』的欄位", df.columns)
    
    if st.button("開始比對"):
        with st.spinner('正在比對漢字與假名...'):
            df['英文成分名'] = df[target_col].apply(lambda x: find_match(x, mapping_list))
            
            # 統計結果
            success_df = df[df['英文成分名'].notna()]
            st.success(f"完成！成功比對 {len(success_df)} 筆，失敗 {len(df)-len(success_df)} 筆。")
            
            st.dataframe(df)

            # 下載
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            st.download_button("📥 下載 Excel 結果", output.getvalue(), "kegg_results.xlsx")
