import streamlit as st
import pandas as pd
import requests
import io
import re

# Azure 認證資訊
AZURE_KEY = "ArkttUAhQYKvd5vh8AB8UTvMiYqNghwaZauenxSLf5A2ptgKtQnHJQQJ99BLAC3pKaRXJ3w3AAAbACOG9KPB"
AZURE_REGION = "eastasia"
AZURE_ENDPOINT = "https://api.cognitive.microsofttranslator.com/translate?api-version=3.0"

st.set_page_config(page_title="KEGG + Azure 藥物譯名工具", layout="wide")

@st.cache_data(ttl=86400)
def get_kegg_mapping():
    url = "https://rest.kegg.jp/list/drug_ja"
    try:
        response = requests.get(url)
        response.encoding = 'utf-8'
        mapping_list = []
        for line in response.text.strip().split('\n'):
            parts = line.split('\t')
            if len(parts) >= 2:
                all_names = [n.strip() for n in parts[1].split('; ')]
                final_en = None
                for name in all_names:
                    has_japanese = re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', name)
                    has_english = re.search(r'[a-zA-Z]{2,}', name)
                    if has_english and not has_japanese:
                        final_en = re.sub(r'[\(（].*?[\)）]', '', name).strip()
                        break 
                
                for name in all_names:
                    clean_key = re.sub(r'[\(（].*?[\)）]', '', name).strip()
                    if re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', clean_key):
                        mapping_list.append({'key': clean_key, 'en': final_en})
        return sorted(mapping_list, key=lambda x: len(x['key']), reverse=True)
    except Exception:
        return []

def translate_with_azure(text):
    """當 KEGG 找不到時，調用 Azure 翻譯"""
    if not text: return None
    headers = {
        'Ocp-Apim-Subscription-Key': AZURE_KEY,
        'Ocp-Apim-Subscription-Region': AZURE_REGION,
        'Content-type': 'application/json'
    }
    # 移除劑型後綴再翻譯以提高準確度
    clean_text = re.sub(r'(錠|注|散|シロップ|液|原末)$', '', str(text))
    body = [{'text': clean_text}]
    params = {'from': 'ja', 'to': 'en'}
    
    try:
        res = requests.post(AZURE_ENDPOINT, params=params, headers=headers, json=body)
        res.raise_for_status()
        result = res.json()
        return result[0]['translations'][0]['text']
    except Exception as e:
        return f"Translation Error: {e}"

def find_match(cell_value, mapping_list):
    if pd.isna(cell_value): return None
    # 全形轉半形
    target = str(cell_value).translate(str.maketrans(
        'ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ０１２３４５６７８９',
        'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    )).replace(' ', '').replace('　', '').strip()
    
    # 1. 嘗試 KEGG 比對
    for item in mapping_list:
        if item['key'] in target and item['en']:
            return item['en'], "KEGG"
    
    # 2. 比對失敗，使用 Azure 翻譯
    translated = translate_with_azure(target)
    return translated, "Azure AI"

# --- UI ---
st.title("💊 藥物譯名終極工具 (KEGG + Azure AI)")
st.info("優先從 KEGG 獲取專業醫學譯名；若無紀錄，則自動透過 Azure Cognitive Services 翻譯。")

mapping_list = get_kegg_mapping()

uploaded_file = st.file_uploader("上傳 XLSX / CSV", type=["xlsx", "csv"])

if uploaded_file:
    df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
    target_col = st.selectbox("選擇成分欄位", df.columns)
    
    if st.button("🚀 開始全自動對照"):
        results = []
        sources = []
        progress_bar = st.progress(0)
        total = len(df)

        for i, val in enumerate(df[target_col]):
            res, src = find_match(val, mapping_list)
            results.append(res)
            sources.append(src)
            progress_bar.progress((i + 1) / total)
        
        df['英文成分名'] = results
        df['來源'] = sources
        
        st.success(f"完成！KEGG 命中: {sources.count('KEGG')} 筆, Azure 翻譯: {sources.count('Azure AI')} 筆")
        st.dataframe(df)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        st.download_button("📥 下載完整結果", output.getvalue(), "medical_translation_final.xlsx")
