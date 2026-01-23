import streamlit as st
import pandas as pd
import os

# 設定網頁配置
st.set_page_config(page_title="藥價查詢系統", layout="wide")

@st.cache_data
def load_combined_data():
    """載入並整合四個來源的檔案"""
    files = {
        "齒科": "medical_translation_final (齒科).xlsx - Sheet1.csv",
        "外用": "medical_translation_final (外用).xlsx - Sheet1.csv",
        "內用": "medical_translation_final (內用).xlsx - Sheet1.csv",
        "注射": "medical_translation_final(注射).xlsx - Sheet1.csv"
    }
    
    all_df = []
    for source_name, file_path in files.items():
        if os.path.exists(file_path):
            # 讀取 CSV，確保藥價欄位為數值
            df = pd.read_csv(file_path)
            # 統一必要欄位
            df = df[['成分名', '英文成分名', '規格', '薬価']].copy()
            df['來源'] = source_name
            # 清洗藥價：移除逗號並轉為浮點數
            df['薬価'] = pd.to_numeric(df['薬価'].astype(str).str.replace(',', ''), errors='coerce')
            all_df.append(df)
        else:
            st.error(f"找不到檔案：{file_path}")
            
    if not all_df:
        return pd.DataFrame()
    
    return pd.concat(all_df, ignore_index=True)

# 載入資料
full_data = load_combined_data()

st.title("💊 藥價聯合查詢系統")
st.write("請輸入日文成分名或英文成分名進行檢索。")

# 查詢介面
search_query = st.text_input("搜尋成分 (日文或英文):", "").strip().lower()

if search_query:
    # 進行模糊搜尋（不分大小寫）
    results = full_data[
        full_data['成分名'].str.contains(search_query, case=False, na=False) |
        full_data['英文成分名'].str.contains(search_query, case=False, na=False)
    ]

    if not results.empty:
        # 分組計算：根據「成分名」與「規格」分組，找出最高/最低藥價與來源
        summary = results.groupby(['成分名', '英文成分名', '規格']).agg({
            '薬価': ['min', 'max', 'count'],
            '來源': lambda x: ', '.join(x.unique())
        }).reset_index()

        # 整理欄位名稱
        summary.columns = ['成分名', '英文成分名', '規格', '最低藥價', '最高藥價', '品項數', '來源']
        
        # 格式化藥價顯示：如果最低等於最高，顯示單一價格；否則顯示範圍
        def format_price(row):
            if row['最低藥價'] == row['最高藥價']:
                return f"¥{row['最低藥價']:,.1f}"
            else:
                return f"¥{row['最低藥價']:,.1f} ~ ¥{row['最高藥價']:,.1f}"

        summary['藥價範圍'] = summary.apply(format_price, axis=1)

        # 顯示結果
        st.subheader(f"🔍 搜尋結果：共找到 {len(summary)} 組規格")
        
        display_df = summary[['成分名', '英文成分名', '規格', '藥價範圍', '來源', '品項數']]
        st.table(display_df)

        # 詳細清單折疊區
        with st.expander("查看原始詳細資料清單"):
            st.dataframe(results.sort_values(by='薬価'))
    else:
        st.warning("查無此成分，請確認輸入是否正確。")

else:
    st.info("請在上方搜尋框輸入關鍵字，例如：「リドカイン」或「Lidocaine」。")

# 側邊欄資訊
st.sidebar.header("資料庫狀態")
if not full_data.empty:
    st.sidebar.write(f"總收錄數量: {len(full_data)} 筆")
    st.sidebar.write("涵蓋範圍：齒科、外用、內用、注射")
