import streamlit as st
import pandas as pd
import requests
import io
import re

# ... (前面 get_kegg_mapping 保持不變) ...

def clean_text(text):
    """清理字串：轉小寫、去空格、移除括號內容"""
    if pd.isna(text):
        return ""
    text = str(text).strip()
    # 移除括號及其內容，例如：アセチルサリチル酸（JAN） -> アセチルサリチル酸
    text = re.sub(r'（[^）]*）', '', text)
    text = re.sub(r'\([^)]*\)', '', text)
    return text.strip()

# --- 在「開始轉換」按鈕內的邏輯修改如下 ---
if st.button("開始轉換"):
    with st.spinner('優化比對中...'):
        # 1. 建立一個「清理過」的對照字典
        # 原本：{"アセチルサリチル酸": "Aspirin"}
        # 這裡確保對照表也是乾淨的
        clean_dict = {clean_text(k): v for k, v in kegg_dict.items()}
        
        # 2. 對 Excel 的欄位進行清理後再比對
        df['temp_clean_col'] = df[target_col].apply(clean_text)
        df['英文成分名'] = df['temp_clean_col'].map(clean_dict)
        
        # 3. 刪除暫存欄位
        df.drop(columns=['temp_clean_col'], inplace=True)
        
        # ... (後續顯示結果與下載) ...
