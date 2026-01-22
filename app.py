import streamlit as st
import pandas as pd
import requests
import io
import re

# 設定網頁標題與佈局
st.set_page_config(page_title="KEGG 藥物成分對照工具", layout="wide")

@st.cache_data(ttl=86400)
def get_kegg_mapping():
    """
    從 KEGG API 獲取資料並建立多重別名對照表
    """
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
                # 原始格式: drug:D01762 \t スルピリン水和物 (JP18); メタミゾールナトリウム水和物; Dipyrone...
                all_names = parts[1].split('; ')
                
                # 找出最後一個名稱（通常是英文）作為基準
                base_en = all_names[-1].strip()
                
                for name in all_names:
                    # 清理名稱：移除 (JP18), (JAN), (USP) 等括號標記
                    clean_name = re.sub(r'[\(（].*?[\)）]', '', name).strip()
                    
                    # 只要包含日文字元 (假名或漢字)，就將其作為 Key 加入對照表
                    if re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', clean_name):
                        mapping_list.append({
                            'key': clean_name,
                            'en_info': "; ".join(all_names) # 存入完整名稱資訊供對照
                        })
        
        # 關鍵：按字串長度由長到短排序，避免短字串(如"水")誤匹配長藥名
        return sorted(mapping_list, key=lambda x: len(x['key']), reverse=True)
    except Exception as e:
        st.error(f"KEGG API 載入失敗: {e}")
        return []

def find_match(cell_value, mapping_list):
    """
    執行包含比對邏輯
    """
    if pd.isna(cell_value):
        return None
    
    # 清理 Excel 儲存格，移除空白以增加命中率
    target = str(cell_value).replace(' ', '').replace('　', '').strip()
    
    for item in mapping_list:
        if item['key'] in target:
            return item['en_info']
    return None

# --- UI 介面 ---
st.title("💊 KEGG 藥物日譯英對照工具 (專業版)")
st.markdown("""
本工具會從 **KEGG DRUG (Japan)** 資料庫抓取最新對照表。
- **支援別名**：如「メタミゾールナトリウム水和物」可正確對應。
- **自動清理**：自動忽略劑型（如"注"、"錠"）與規格。
""")

mapping_list = get_kegg_mapping()

if mapping_list:
    st.sidebar.success(f"✅ 已載入 {len(mapping_list)} 筆成分別名")
    
uploaded_file = st.file_uploader("請上傳 XLSX 或 CSV 檔案", type=["xlsx", "csv"])

if uploaded_file:
    # 自動偵測編碼讀取
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, encoding='utf-8')
        else:
            df = pd.read_excel(uploaded_file)
    except UnicodeDecodeError:
        df = pd.read_csv(uploaded_file, encoding='shift-jis')

    target_col = st.selectbox("請選擇『成分名』所在的欄位", df.columns)
    
    if st.button("🚀 開始比對轉換"):
        with st.spinner('正在比對中，請稍候...'):
            # 執行比對
            df['KEGG_完整對照資訊'] = df[target_col].apply(lambda x: find_match(x, mapping_list))
            
            # 計算成功筆數
            success_count = df['KEGG_完整對照資訊'].notna().sum()
            fail_count = len(df) - success_count
            
            st.divider()
            st.subheader("比對結果摘要")
            col1, col2 = st.columns(2)
            col1.metric("成功筆數", f"{success_count} 筆")
            col2.metric("失敗筆數", f"{fail_count} 筆")
            
            st.dataframe(df)

            # 產生下載檔案
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            
            st.download_button(
                label="📥 下載完整結果 Excel",
                data=output.getvalue(),
                file_name="kegg_translation_results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
