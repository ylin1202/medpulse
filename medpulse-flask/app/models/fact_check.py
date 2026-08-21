from app.utils.db import Database


class FactCheckModel:
    """Data Access Object (DAO) for querying PUBHEALTH public health fact-checking records."""

    @staticmethod
    def get_list(page=1, limit=10, keyword=None):
        """
        Retrieve a paginated list of fact-checked claims with keyword search support.

        Note: Explicitly selects projection columns and excludes high-dimensional 
        vector embeddings to optimize API throughput and serialization latency.
        """
        offset = (page - 1) * limit
        params = []
        
        # Base SQL query (excluding vector embeddings)
        base_query = """
            SELECT id, claim, explanation, label, claim_url, main_text, sources
            FROM factcheck_vectors
        """
        count_query = "SELECT COUNT(*) FROM factcheck_vectors"
        
        where_clause = ""
        if keyword:
            where_clause = " WHERE claim ILIKE %s OR explanation ILIKE %s"
            search_pattern = f"%{keyword}%"
            params.extend([search_pattern, search_pattern])

        # Retrieve total matching count for pagination metadata
        total_count_res = Database.execute_query(
            count_query + where_clause, 
            params=params if keyword else None, 
            fetchone=True
        )
        total_items = total_count_res["count"] if total_count_res else 0

        # Retrieve paginated records
        query = f"{base_query}{where_clause} ORDER BY id ASC LIMIT %s OFFSET %s;"
        query_params = params + [limit, offset]
        
        items = Database.execute_query(query, params=query_params, fetchall=True) or []

        return {
            "items": items,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_items": total_items,
                "total_pages": (total_items + limit - 1) // limit if limit > 0 else 0
            }
        }

    @staticmethod
    def get_by_id(item_id):
        """Retrieve detailed information for a specific fact-check record by ID."""
        query = """
            SELECT id, claim, explanation, label, claim_url, main_text, sources
            FROM factcheck_vectors
            WHERE id = %s;
        """
        return Database.execute_query(query, (item_id,), fetchone=True)