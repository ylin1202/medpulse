from app.utils.db import Database


class PharmacyModel:
    """Data Access Object (DAO) for querying contracted pharmacy records and geolocation data."""

    @staticmethod
    def get_all(keyword=None, city=None):
        """
        Retrieve a list of pharmacies supporting keyword search and administrative city filtering.
        """
        params = []
        conditions = []

        query = """
            SELECT id, name, status, city, district, address, phone, is_nhi_contracted, latitude, longitude
            FROM pharmacies
        """

        # Keyword search (matches pharmacy name or physical address)
        if keyword:
            conditions.append("(name ILIKE %s OR address ILIKE %s)")
            pattern = f"%{keyword}%"
            params.extend([pattern, pattern])

        # Filter by administrative region/city (e.g., Taipei City)
        if city:
            conditions.append("city = %s")
            params.append(city)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY id ASC;"

        return Database.execute_query(query, params=params if conditions else None, fetchall=True) or []