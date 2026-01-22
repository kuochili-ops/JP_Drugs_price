import streamlit as st
import pandas as pd
import requests
import io
import re

st.set_page_config(page_title="KEGG 藥物精確譯名工具", layout="wide")

@st.cache_data(ttl=86400)
def get_kegg_mapping():
    url = "https://rest.kegg.jp/list/drug_ja"
    try:
        response = requests.get(url)
        response.encoding = 'utf-8'
        if response.status_code != 200:
            return []
        
        mapping_list = []
        for line in response.text.strip().split('\n'):
            parts = line.split('\t')
            if len(parts) >= 2:
                # 原始字串範例: "別名1; 別名2; Botulinum toxin; (JAN)"
                all_names = [n.strip() for n in parts[1].split('; ')]
                
                # --- 核心邏輯：尋找第一個合格的英文名詞 ---
                final_en = "N/A"
                for name in all_names:
                    # 檢查是否為英文：判斷是否包含多個英文字母，且不包含日文字元 (假名/漢字)
                    # 我們排除掉純日文項，直到找到主要為英文的項目
                    has_japanese = re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', name)
                    has_english = re.search(r'[a-zA-Z]{2,}', name) # 至少包含兩個英文字母
                    
                    if has_english and not has_japanese:
                        # 找到後，移除括號標註如 (JAN), (USP)
                        final_en = re.sub(r'[\(（].*?[\)）]', '', name).strip()
                        break 
                
                # --- 建立所有日文別名對應到該英文名的索引 ---
                for name in all_names:
                    clean_key = re.sub(r'[\(（].*?[\)）]', '', name).strip()
                    # 只要該別名包含日文字，就當作 Key
                    if re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', clean_key):
                        mapping_list.append({
                            'key': clean_key,
                            'en': final_en
                        })
        
        # 按長度排序，確保「アムロジピンベシル酸塩」先於「アムロジピン」
        return sorted(mapping_list, key=lambda x: len(x['key']), reverse=True)
    except Exception as e:
        st.error(f"API 載入失敗: {e}")
        return []

def find_match(cell_value, mapping_list):
    if pd.isna(cell_value): return None
    # 正規化 Excel 內容：統一全形英數為半形，並移除空格
    target = str(cell_value).translate(str.maketrans('ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ０１２３４５６７８９', 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789')).replace(' ', '').replace('　', '').strip()
    
    for item in mapping_list:
        if item['key'] in target:
            return item['en']
    return None

# --- UI 介面 ---
st.title("💊 KEGG 藥物日譯英 (精確英文過濾版)")
st.info("規則：搜尋分號標籤，排除日文別名，直到找到純英文名詞為止。")

mapping_list = get_kegg_mapping()

uploaded_file = st.file_uploader("上傳 XLSX 或 CSV", type=["xlsx", "csv"])

if uploaded_file:
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, encoding='utf-8')
        else:
            df = pd.read_excel(uploaded_file)
    except UnicodeDecodeError:
        df = pd.read_csv(uploaded_file, encoding='shift-jis')

    target_col = st.selectbox("請選擇『成分名』欄位", df.columns)
    
    if st.button("🚀 開始執行"):
        with st.spinner('逐層分析別名中...'):
            df['英文成分名'] = df[target_col].apply(lambda x: find_match(x, mapping_list))
            st.success("比對完成！已過濾掉中間的日文別名。")
            st.dataframe(df)

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            st.download_button("📥 下載 Excel 結果", output.getvalue(), "kegg_translation_final.xlsx")
