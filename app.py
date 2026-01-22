import streamlit as st
import pandas as pd
import requests
import io
import re

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
                names = parts[1].split('; ')
                if len(names) >= 2:
                    raw_jp = names[0].strip()
                    # 清理 API 名稱：移除 (JP18), (JAN) 等括號內容
                    clean_jp = re.sub(r'[\(（].*?[\)）]', '', raw_jp).strip()
                    
                    mapping_list.append({
                        'clean_jp': clean_jp,
                        'en': names[1].strip()
                    })
        # 按長度排序，確保「アムロジピンベシル酸塩」先於「アムロジピン」被匹配
        return sorted(mapping_list, key=lambda x: len(x['clean_jp']), reverse=True)
    except Exception as e:
        st.error(f"KEGG 連線失敗: {e}")
        return []

def find_match(cell_value, mapping_list):
    if pd.isna(cell_value):
        return None
    cell_str = str(cell_value).strip()
    
    # 邏輯：檢查 API 的 clean_jp 是否出現在 Excel 儲存格中
    # 例如：'ドロペリドール' 是否在 'ドロペリドール注' 裡面
    for item in mapping_list:
        if item['clean_jp'] and item['clean_jp'] in cell_str:
            return item['en']
    return None

# --- UI 介面部分保持不變 ---
