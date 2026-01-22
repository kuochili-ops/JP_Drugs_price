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
                # 取得所有名稱 (包含別名)，例如 ["スルピリン水和物 (JP18)", "メタミゾールナトリウム水和物", "Dipyrone..."]
                all_names = parts[1].split('; ')
                
                # 找出第一個看起來像英文的索引 (通常英文名在日文名之後)
                # 我們把前面的日文別名全部抓出來
                en_name = all_names[-1] # 預設最後一個是英文 (或是包含多國語言)
                
                for name in all_names:
                    # 如果該名稱包含英文字母超過 3 個，通常就不是日文主成分名，我們跳過它作為 Key
                    # 但保留它作為最終輸出的英文參考
                    clean_jp = re.sub(r'[\(（].*?[\)）]', '', name).strip()
                    
                    # 只要這個名字含有日文字元 (平假名、片假名、漢字)，就把它加入對照表
                    if re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', clean_jp):
                        mapping_list.append({
                            'clean_jp': clean_jp,
                            'en': "; ".join(all_names[1:]) # 回傳除了第一個以外的所有別名作為參考
                        })
        
        # 排序：長名優先
        return sorted(mapping_list, key=lambda x: len(x['clean_jp']), reverse=True)
    except Exception as e:
        st.error(f"API 連線異常: {e}")
        return []
