from typing import Any, Dict, List, Optional
import asyncpg

from app.core.logging import logger


async def query_medical_metrics_async(
    metrics_list: List[str], 
    db_pool: Optional[asyncpg.Pool]
) -> Dict[str, Any]:
    """
    Asynchronously retrieve reference ranges and definitions for clinical lab metrics.
    Batch queries PostgreSQL to prevent N+1 overhead and handles basic lemmatization.
    """
    if not metrics_list or db_pool is None:
        return {}

    cleaned_metrics = [m.strip().lower() for m in metrics_list if m.strip()]
    if not cleaned_metrics:
        return {}

    # Include singularized variations to account for pluralized metric inputs
    search_terms = set(cleaned_metrics)
    for m in cleaned_metrics:
        if m.endswith("s") and len(m) > 1:
            search_terms.add(m[:-1])

    query = """
        SELECT 
            metric_label, 
            ref_range_lower, 
            ref_range_upper, 
            valueuom, 
            metric_definition 
        FROM medical_metrics 
        WHERE LOWER(metric_label) = ANY($1::text[])
           OR LOWER(REGEXP_REPLACE(metric_label, 's$', '')) = ANY($1::text[]);
    """

    results = {}
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(query, list(search_terms))
            for row in rows:
                label = row["metric_label"]
                results[label] = {
                    "lower": float(row["ref_range_lower"]) if row["ref_range_lower"] is not None else None,
                    "upper": float(row["ref_range_upper"]) if row["ref_range_upper"] is not None else None,
                    "unit": row["valueuom"],
                    "definition": row["metric_definition"]
                }
    except Exception as e:
        logger.error("[PostgreSQL Async RAG Error] Failed to query medical metrics: %s", e, exc_info=True)
        return {}

    return results


async def hybrid_search_fallback_async(
    query_text: str,
    query_embedding: List[float],
    db_pool: Optional[asyncpg.Pool],
    top_k: int = 3,
    rrf_k: int = 60
) -> List[Dict[str, Any]]:
    """
    Perform hybrid vector search (Dense Cosine Similarity + Sparse Full-Text Search)
    fused with Reciprocal Rank Fusion (RRF) for semantic metric retrieval.
    """
    if not query_text or db_pool is None:
        return []

    hybrid_sql = """
    WITH dense_search AS (
        SELECT id, metric_label, ref_range_lower, ref_range_upper, valueuom, metric_definition,
               ROW_NUMBER() OVER (ORDER BY embedding <=> $1::vector) as dense_rank
        FROM medical_metrics
        WHERE embedding IS NOT NULL
        LIMIT 20
    ),
    sparse_search AS (
        SELECT id, metric_label, ref_range_lower, ref_range_upper, valueuom, metric_definition,
               ROW_NUMBER() OVER (ORDER BY ts_rank_cd(search_vector, plainto_tsquery('english', $2)) DESC) as sparse_rank
        FROM medical_metrics
        WHERE search_vector @@ plainto_tsquery('english', $2)
        LIMIT 20
    )
    SELECT 
        COALESCE(d.id, s.id) as id,
        COALESCE(d.metric_label, s.metric_label) as metric_label,
        COALESCE(d.ref_range_lower, s.ref_range_lower) as ref_range_lower,
        COALESCE(d.ref_range_upper, s.ref_range_upper) as ref_range_upper,
        COALESCE(d.valueuom, s.valueuom) as valueuom,
        COALESCE(d.metric_definition, s.metric_definition) as metric_definition,
        COALESCE(1.0 / ($3 + d.dense_rank), 0.0) +
        COALESCE(1.0 / ($3 + s.sparse_rank), 0.0) as rrf_score
    FROM dense_search d
    FULL OUTER JOIN sparse_search s ON d.id = s.id
    ORDER BY rrf_score DESC
    LIMIT $4;
    """

    results = []
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(hybrid_sql, str(query_embedding), query_text, rrf_k, top_k)
            for row in rows:
                results.append({
                    "metric_label": row["metric_label"],
                    "lower": float(row["ref_range_lower"]) if row["ref_range_lower"] is not None else None,
                    "upper": float(row["ref_range_upper"]) if row["ref_range_upper"] is not None else None,
                    "unit": row["valueuom"],
                    "definition": row["metric_definition"],
                    "rrf_score": float(row["rrf_score"])
                })
    except Exception as e:
        logger.error("[Hybrid Search Error] Failed executing hybrid search fallback for query '%s': %s", query_text, e, exc_info=True)

    return results