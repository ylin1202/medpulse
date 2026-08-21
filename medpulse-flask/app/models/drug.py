from app.utils.db import Database


class DrugModel:
    """Data Access Object (DAO) for querying OpenFDA drug records."""

    @staticmethod
    def get_list(page=1, limit=10, keyword=None, product_type=None):
        """
        Retrieve a paginated list of drugs with keyword search and product type filtering.

        Note: Excludes large raw payload columns (e.g., raw_openfda) to optimize transfer throughput.
        """
        offset = (page - 1) * limit
        params = []
        conditions = []

        base_query = """
            SELECT id, brand_name, generic_name, manufacturer_name, product_type, route, active_ingredient, purpose, boxed_warning
            FROM drugs
        """
        count_query = "SELECT COUNT(*) FROM drugs"

        # Keyword search (matches brand name, generic name, or therapeutic purpose)
        if keyword:
            conditions.append("(brand_name ILIKE %s OR generic_name ILIKE %s OR purpose ILIKE %s)")
            pattern = f"%{keyword}%"
            params.extend([pattern, pattern, pattern])

        # Filter by product category (e.g., HUMAN OTC DRUG or PRESCRIPTION)
        if product_type:
            conditions.append("product_type = %s")
            params.append(product_type)

        where_clause = ""
        if conditions:
            where_clause = " WHERE " + " AND ".join(conditions)

        # Retrieve total record count matching criteria
        total_res = Database.execute_query(
            count_query + where_clause, 
            params=params if conditions else None, 
            fetchone=True
        )
        total_items = total_res["count"] if total_res else 0

        # Retrieve paginated dataset
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
    def get_by_id(drug_id):
        """Retrieve complete drug package insert details by drug ID."""
        query = "SELECT * FROM drugs WHERE id = %s;"
        return Database.execute_query(query, (drug_id,), fetchone=True)