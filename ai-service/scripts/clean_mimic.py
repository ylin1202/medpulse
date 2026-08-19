import pandas as pd
import os

def build_rag_base():
    """
    這個函式負責把原始的 MIMIC-IV 壓縮檔解壓、關聯(Merge)、清洗，
    並挑選出最核心的前 20 個醫學指標，作為我們 RAG 知識庫的地基。
    """
    print("1. 正在讀取並解壓 data/ 目錄下的 MIMIC-IV 原始檔案...")
    
    # 【安全防護】檢查所需的原始檔案是否存在於 data/ 資料夾中，避免路徑錯誤直接噴 bug
    if not os.path.exists('data/d_labitems.csv.gz'):
        print("錯誤：找不到 data/d_labitems.csv.gz，請檢查你的專案目錄結構！")
        return

    d_labitems = pd.read_csv('data/d_labitems.csv.gz', compression='gzip')       # 檢驗指標字典檔 (對照表)
    labevents = pd.read_csv('data/labevents.csv.gz', compression='gzip')         # 病患檢驗紀錄檔 (內含數據與正常值)
    d_icd = pd.read_csv('data/d_icd_diagnoses.csv.gz', compression='gzip')       # ICD 疾病診斷字典檔
    
    print("2. 正在關聯檢驗指標與正常值範圍 (Merge / Inner Join)...")
    # 【資料關聯】利用兩張表共有的 'itemid' 進行 Inner Join，把「檢驗數值」和「指標名稱」拼在一起
    lab_merged = pd.merge(labevents, d_labitems, on='itemid', how='inner')
    
    print("3. 清洗無效數據，篩選核心欄位...")
    # 【欄位篩選】我們只需要：指標ID、名稱、檢驗流體(如血液)、類別、正常值下限、正常值上限、單位
    # 【清洗過濾】.dropna() 負責強制「移除」參考範圍（ref_range_lower/upper）是 Null 空值的無效紀錄
    lab_filtered = lab_merged[[
        'itemid', 'label', 'fluid', 'category', 
        'ref_range_lower', 'ref_range_upper', 'valueuom'
    ]].dropna(subset=['ref_range_lower', 'ref_range_upper'])
    
    print("4. 統計出現頻率，篩選前 20 個最常用的核心檢驗指標...")
    # 【統計排序】value_counts() 會計算每個 itemid 在病歷中出現了幾次，.head(20).index 負責抓出前 20 名的 ID 清單
    top_items_counts = lab_filtered['itemid'].value_counts().head(20).index
    
    # 【去重篩選】
    # .isin()：只保留屬於前 20 名核心指標的紀錄
    # drop_duplicates()：因為同一個指標有很多紀錄，我們用 itemid 去重，每個指標只留一筆作為資料庫字典的定義
    final_metrics = lab_filtered[lab_filtered['itemid'].isin(top_items_counts)].drop_duplicates(subset=['itemid'])
    
    # 【成果打印】在終端機印出這 20 筆指標，確認成果
    print(f"\n 成功洗出 {len(final_metrics)} 筆核心醫學指標！")
    print("=" * 70)
    print(final_metrics[['itemid', 'label', 'ref_range_lower', 'ref_range_upper', 'valueuom']].to_string(index=False))
    print("=" * 70)
    
    # 【資料導出】將清洗好的指標基礎表格，儲存回 data 資料夾，準備下一階段塞進 PostgreSQL
    final_metrics.to_csv('data/cleaned_metrics_base.csv', index=False)
    print("指標基礎檔已儲存至 data/cleaned_metrics_base.csv")
    
    print("\n🩺 5. 正在篩選前 20 個常見 ICD 疾病診斷...")
    # 【疾病篩選】先抽取前 20 個 ICD 疾病名稱作為我們的 RAG 疾病查詢範本
    top_diseases = d_icd.head(20)
    
    # 【資料導出】儲存疾病基礎表格
    top_diseases.to_csv('data/cleaned_diseases_base.csv', index=False)
    print("疾病基礎檔已儲存至 data/cleaned_diseases_base.csv")
    print("【階段一第一步】資料清洗全部完成！")

if __name__ == "__main__":
    # 當在終端機執行 python scripts/clean_mimic.py 時，會觸發執行上面的函式
    build_rag_base()