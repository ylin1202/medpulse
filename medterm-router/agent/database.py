import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

async def query_medical_metrics_async(metrics_list: list, db_pool: asyncpg.Pool) -> dict:
    # 防呆機制：若沒傳入 metrics_list 或 db_pool 為 None，直接返回空字典
    if not metrics_list or not db_pool:
        print("  └─ [DB Debug] db_pool is None or metrics_list is empty!")
        return {}

    results = {}
    try:
        async with db_pool.acquire() as conn:
            for metric in metrics_list:
                clean_metric = metric.strip()
                if not clean_metric:
                    continue

                row = None

                # 1. 精確比對（不分大小寫）
                exact_query = """
                    SELECT metric_label, ref_range_lower, ref_range_upper, valueuom, metric_definition 
                    FROM medical_metrics 
                    WHERE LOWER(metric_label) = LOWER($1);
                """
                row = await conn.fetchrow(exact_query, clean_metric)

                # 2. 自動去複數 's' 比對 (如 White Blood Cells -> White Blood Cell)
                if not row and clean_metric.lower().endswith('s'):
                    singular_metric = clean_metric[:-1]
                    row = await conn.fetchrow(exact_query, singular_metric)

                # 3. 關鍵字模糊比對 (ILIKE)
                if not row:
                    fuzzy_query = """
                        SELECT metric_label, ref_range_lower, ref_range_upper, valueuom, metric_definition 
                        FROM medical_metrics 
                        WHERE metric_label ILIKE $1 
                        LIMIT 1;
                    """
                    row = await conn.fetchrow(fuzzy_query, f"%{clean_metric}%")

                # 4. 若查到資料，封裝結果
                if row:
                    results[row['metric_label']] = {
                        "lower": float(row['ref_range_lower']) if row['ref_range_lower'] is not None else None,
                        "upper": float(row['ref_range_upper']) if row['ref_range_upper'] is not None else None,
                        "unit": row['valueuom'],
                        "definition": row['metric_definition']
                    }
                else:
                    print(f"  └─ [DB Miss] '{clean_metric}' not matched in medical_metrics table.")

    except Exception as e:
        print(f"[PostgreSQL Async RAG Error]: {e}")

    return results