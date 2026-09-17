"""
Compatibility layer for the CockroachDB migration branch.

The existing scrapers import `create_client` from `supabase` and use a small
subset of the Supabase Python API.  This module intentionally keeps that API
surface while storing data directly in CockroachDB through psycopg.

Required environment variable:
    DATABASE_URL=postgresql://.../defaultdb?sslmode=verify-full
"""

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable

import psycopg
from psycopg import sql
from psycopg.rows import dict_row


@dataclass
class _Response:
    data: list[dict[str, Any]]


_CONFLICT_COLUMNS = {
    "Gare": ["id_gara_fisi"],
    "Risultati": ["id_gara_fisi", "atleta_nome", "categoria", "posizione"],
    "Risultati_Fis": ["id_gara_fis", "atleta_nome", "categoria", "posizione"],
}


def _parse_date(value: Any):
    """Best-effort conversion for the auxiliary DATE column data_gara_iso."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.upper() in {"N/D", "NULL", "NONE"}:
        return None

    formats = (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d.%m.%Y",
        "%Y/%m/%d",
        "%B %d, %Y",
        "%d %b %Y",
    )
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


class _TableQuery:
    def __init__(self, client: "_CockroachClient", table: str):
        self.client = client
        self.table = table
        self._operation = "select"
        self._columns = "*"
        self._filters: list[tuple[str, Any]] = []
        self._limit: int | None = None
        self._upsert_data: list[dict[str, Any]] = []

    def select(self, columns: str = "*"):
        self._operation = "select"
        self._columns = columns
        return self

    def eq(self, column: str, value: Any):
        self._filters.append((column, value))
        return self

    def limit(self, value: int):
        self._limit = int(value)
        return self

    def upsert(self, data: Any):
        self._operation = "upsert"
        if isinstance(data, dict):
            self._upsert_data = [dict(data)]
        else:
            self._upsert_data = [dict(row) for row in data]
        return self

    def execute(self) -> _Response:
        if self._operation == "upsert":
            return self._execute_upsert()
        return self._execute_select()

    def _execute_select(self) -> _Response:
        if self._columns.strip() == "*":
            column_sql = sql.SQL("*")
        else:
            names = [name.strip() for name in self._columns.split(",") if name.strip()]
            column_sql = sql.SQL(", ").join(sql.Identifier(name) for name in names)

        query = sql.SQL("SELECT {} FROM {}").format(
            column_sql,
            sql.Identifier(self.table),
        )
        params: list[Any] = []

        if self._filters:
            clauses = []
            for column, value in self._filters:
                clauses.append(sql.SQL("{} = %s").format(sql.Identifier(column)))
                params.append(value)
            query += sql.SQL(" WHERE ") + sql.SQL(" AND ").join(clauses)

        if self._limit is not None:
            query += sql.SQL(" LIMIT %s")
            params.append(self._limit)

        with self.client.connection.cursor(row_factory=dict_row) as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
        return _Response(data=[dict(row) for row in rows])

    def _execute_upsert(self) -> _Response:
        if not self._upsert_data:
            return _Response(data=[])

        conflict_columns = _CONFLICT_COLUMNS.get(self.table)
        if not conflict_columns:
            raise ValueError(f"Nessuna chiave di conflitto configurata per la tabella {self.table}")

        prepared: list[dict[str, Any]] = []
        for original in self._upsert_data:
            row = dict(original)
            if "data_gara" in row and "data_gara_iso" not in row:
                row["data_gara_iso"] = _parse_date(row.get("data_gara"))
            prepared.append(row)

        columns = list(prepared[0].keys())
        for row in prepared:
            if list(row.keys()) != columns:
                raise ValueError("Tutti i record dello stesso batch devono avere le stesse colonne")

        insert_columns = sql.SQL(", ").join(sql.Identifier(c) for c in columns)
        placeholders = sql.SQL(", ").join(sql.Placeholder() for _ in columns)
        conflict_sql = sql.SQL(", ").join(sql.Identifier(c) for c in conflict_columns)

        update_columns = [c for c in columns if c not in conflict_columns and c != "id"]
        if update_columns:
            assignments = sql.SQL(", ").join(
                sql.SQL("{} = excluded.{}").format(sql.Identifier(c), sql.Identifier(c))
                for c in update_columns
            )
            action = sql.SQL("DO UPDATE SET ") + assignments
        else:
            action = sql.SQL("DO NOTHING")

        query = sql.SQL(
            "INSERT INTO {} ({}) VALUES ({}) ON CONFLICT ({}) {}"
        ).format(
            sql.Identifier(self.table),
            insert_columns,
            placeholders,
            conflict_sql,
            action,
        )

        values: Iterable[tuple[Any, ...]] = [
            tuple(row.get(column) for column in columns) for row in prepared
        ]

        with self.client.connection.cursor() as cur:
            cur.executemany(query, values)

        return _Response(data=prepared)


class _CockroachClient:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self._connection = None

    @property
    def connection(self):
        if self._connection is None or self._connection.closed:
            self._connection = psycopg.connect(
                self.database_url,
                autocommit=True,
                connect_timeout=20,
            )
        return self._connection

    def table(self, name: str) -> _TableQuery:
        return _TableQuery(self, name)


def create_client(_url: str | None = None, _key: str | None = None):
    """Drop-in replacement for the limited Supabase API used by the scrapers."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("Variabile DATABASE_URL mancante")
    return _CockroachClient(database_url)
