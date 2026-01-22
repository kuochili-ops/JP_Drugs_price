import streamlit as st
import pandas as pd
import requests
import io
import re

st.set_page_config(page_title="KEGG 藥物成分對照工具", layout="wide")

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
                # 原始字串範例: "A型ボツリヌス毒素 (JAN); Botulinum toxin type A (JAN)"
                full_name_str = parts[1]
                all_names = full_name_str.split('; ')
                
                # 篩選出真正的英文名：通常在分號後，且包含英文字母
                # 我們找尋包含 [a-zA-Z] 的項目作為英文輸出
                english_names = [n for n in all_names if re.search(r'[a-zA-Z]', n)]
                # 如果有找到英文名，取第一個並清理掉 (JAN) 等括號
                final_en = ""
                if english_names:
                    final_en = re.sub(r'[\(（].*?[\)）]', '', english_names[0]).strip()
                
                # 建立日文 Key 對應這組英文名
                for name in all_names:
                    # 清理日文 Key (移除括號)
                    clean_key = re.sub(r'[\(（].*?[\)）]', '', name).strip()
                    
                    # 只要 Key 包含日文字元，就加入對照表
                    if re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', clean_key):
                        mapping_list.append({
                            'key': clean_key,
                            'en': final_en if final_en else "N/A"
                        })
        
        return sorted(mapping_list, key=lambda x: len(x['key']), reverse=True)
    except Exception as e:
        st.error(f"API 載入失敗: {e}")
        return []

def find_match(cell_value, mapping_list):
    if pd.isna(cell_value): return None
    target = str(cell_value).replace(' ', '').replace('　', '').strip()
    
    for item in mapping_list:
        if item['key'] in target:
            return item['en']
    return None

# --- UI 介面 ---
st.title("💊 KEGG 藥物日譯英對照工具 (精確擷取版)")
st.info("規則：自動匹配日文成分，並僅擷取分號（;）後方之英文名詞。")

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
    
    if st.button("🚀 開始轉換"):
        with st.spinner('比對中...'):
            df['英文成分名'] = df[target_col].apply(lambda x: find_match(x, mapping_list))
            
            st.success(f"轉換完成！已根據分號後的英文名稱進行擷取。")
            st.dataframe(df)

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            
            st.download_button(
                label="📥 下載 Excel 結果",
                data=output.getvalue(),
                file_name="kegg_english_results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
