import pandas as pd
import json
import random

def generate_fine_tune_data():
    print("1. 讀取 20 個核心指標當作基礎標籤...")
    try:
        # 讀取階段一洗出來的 20 個熱門醫療指標基礎檔案
        df = pd.read_csv('data/cleaned_metrics_base.csv')
        # 【資料清洗】使用 .strip() 強制修剪掉指標名稱字串前後可能隱藏的空格，防範未來字串比對失敗
        metrics_list = [str(m).strip() for m in df['label'].tolist()]
    except Exception as e:
        print("錯誤：找不到 data/cleaned_metrics_base.csv，請先確保階段一腳本已執行！")
        return

    # 【多樣化語境設計】建立 2 個醫學指標的模擬病歷句型庫，涵蓋急診、查房、主訴等情境
    templates_2_metrics = [
        "Patient was admitted to the ER presenting with extreme fatigue and pale skin. Emergency physician requested immediate screening for {metrics}.",
        "The laboratory report came back showing fluctuating levels of {m1}. However, {m2} appears perfectly stable within normal ranges.",
        "During the morning rounds, the attending doctor noted that the patient's chronic condition is slightly deteriorating. Recommend checking {metrics}.",
        "Routine health check-up panel completed. The primary care provider highlighted borderline abnormal findings in {m1}. {m2} is tracked as control.",
        "The patient's family requested a simplified explanation of the morning lab results, specifically asking about the values of {metrics}.",
        "Pre-operative evaluation requires a comprehensive clearance. Ensure that {metrics} are documented in the pre-op chart.",
        "The telemedicine consultation note indicates the need to re-verify past lab charts. Prioritize tracking historical trends for {metrics}.",
        "Discharge summary draft: Patient is stable to leave. Outpatient clinic follow-up scheduled in 2 weeks to re-test {metrics}."
    ]

    # 【高難度語境設計】建立 3 個醫學指標的重症或加護病房（ICU）句型庫
    templates_3_metrics = [
        "Clinical note from ICU: please monitor the patient's vital signs and run automated panels for {metrics} every 12 hours.",
        "Post-op recovery progress is acceptable. Follow-up blood work is ordered for tomorrow morning to evaluate {metrics}.",
        "Physician initial assessment: symptoms indicate potential metabolic stress. Request full panel including {metrics} immediately."
    ]

    dataset = []
    print("2. 開始交叉合成 120 筆高泛化性的訓練資料...")

    # 執行循環，動態組裝 120 筆「輸入(病歷) -> 輸出(JSON)」的配對範例
    for i in range(120):
        # 隨機決定這一筆範例要塞 2 個還是 3 個指標，模擬真實病歷的隨機性
        num_metrics = random.choice([2, 3])
        # 從 20 個核心清單中，隨機抽出不重複的指標
        chosen_metrics = random.sample(metrics_list, num_metrics)
        
        # 【自然語言拼裝】動態組裝符合英文文法的 "A and B" 或 "A, B, and C" 語句
        if num_metrics == 2:
            metrics_string = f"{chosen_metrics[0]} and {chosen_metrics[1]}"
            template = random.choice(templates_2_metrics)
            # 將組裝好的指標字串或單一指標，填入對應的模板變數中
            input_text = template.format(metrics=metrics_string, m1=chosen_metrics[0], m2=chosen_metrics[1])
        else:
            # 包含牛津逗號（Oxford Comma）的標準英文三項串接文法
            metrics_string = f"{chosen_metrics[0]}, {chosen_metrics[1]}, and {chosen_metrics[2]}"
            template = random.choice(templates_3_metrics)
            input_text = template.format(metrics=metrics_string)

        # ====================================================================
        # 【核心算法優化：破除死記硬背】
        # 故意用 random.shuffle() 打亂 output JSON 陣列裡的指標順序。
        # 如果 input 出現順序和 output 永遠相同，AI 會偷懶唯讀「相對位置」；打亂順序能強迫模型真正理解語意！
        # ====================================================================
        extracted_metrics = list(chosen_metrics)
        random.shuffle(extracted_metrics) 
        
        # 構建小模型的思考鏈 (Chain of Thought)，植入「禁止越界給醫療診斷」的安全潛意識
        thought_process = (
            f"The clinical input mentions {', '.join(extracted_metrics)}. "
            f"To comply with safety guardrails and prevent illegal medical diagnosis, "
            f"I must extract these exact terms as raw database query keys without adding any medical opinions."
        )
        
        # 封裝成微調需要的目標輸出格式
        output_json = {
            "thought": thought_process,
            "query": extracted_metrics
        }
        
        # 【格式特訓設計】使用 indent=2 讓 output 變成帶有漂亮換行和縮排的標準 JSON 字串。
        # 這樣微調時可以硬生生把「只吐乾淨 JSON」的格式紀律印入模型的潛意識，防止未來半空噴出亂碼。
        data_entry = {
            "instruction": "Extract valid medical metrics from the clinical text. Output JSON only.",
            "input": input_text,
            "output": json.dumps(output_json, ensure_ascii=False, indent=2)
        }
        dataset.append(data_entry)

    print(f"3. 正在將 {len(dataset)} 筆商用級訓練集寫入 data/train.json...")
    # 將組裝完成的 120 筆高畫質教科書範例存入 data 資料夾
    with open('data/train.json', 'w', encoding='utf-8') as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
        
    print("【階段二第一步】本地訓練集原料製作成功！")

if __name__ == "__main__":
    generate_fine_tune_data()