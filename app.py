import streamlit as st
import pandas as pd
import requests
import io

st.set_page_config(page_title="藥物日譯英工具", layout="wide")

@st.cache_data(ttl=86400)
def get_kegg_mapping():
    url = "https://rest.kegg.jp/list/drug_ja"
    try:
        response = requests.get(url)
        response.raise_for_status()
        # 建立一個清單，按名稱長度排序（長到短），確保比對時先匹配最完整的名稱
        mapping_list = []
        for line in response.text.strip().split('\n'):
            parts = line.split('\t')
            if len(parts) >= 2:
                names = parts[1].split('; ')
                if len(names) >= 2:
                    mapping_list.append({
                        'jp': names[0].strip(),
                        'en': names[1].strip()
                    })
        # 排序：長名在前，避免「アスピリン」先匹配到「アスピリン・アスコルビン酸」
        return sorted(mapping_list, key=lambda x: len(x['jp']), reverse=True)
    except Exception as e:
        st.error(f"KEGG 連線失敗: {e}")
        return []

def find_match(cell_value, mapping_list):
    if pd.isna(cell_value):
        return None
    cell_str = str(cell_value)
    # 在對照表中尋找是否存在於儲存格字串中
    for item in mapping_list:
        if item['jp'] in cell_str:
            return item['en']
    return None

st.title("💊 藥物成分日譯英 (針對規格描述優化版)")

mapping_list = get_kegg_mapping()

uploaded_file = st.file_uploader("上傳您的藥物清單 (XLSX/CSV)", type=["xlsx", "csv"])

if uploaded_file:
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
        
    target_col = st.selectbox("請選擇成分欄位", df.columns, index=0)

    if st.button("執行比對"):
        with st.spinner('比對中... 這可能需要幾秒鐘'):
            # 執行包含比對
            df['對應英文成分'] = df[target_col].apply(lambda x: find_match(x, mapping_list))
            
            match_rate = df['對應英文成分'].notna().mean() * 100
            st.success(f"比對完成！成功率：{match_rate:.1f}%")
            st.dataframe(df)

            # 下載模組
            output = io.BytesIO()
            df.to_excel(output, index=False)
            st.download_button("下載結果", output.getvalue(), "result.xlsx")
