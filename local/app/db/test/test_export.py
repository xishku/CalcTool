"""测试导出工具：export_csv / export_json"""

import csv
import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dbutil import DB, Connection


@pytest.fixture
def sample_rows():
    return [
        {"id": 1, "name": "Alice", "score": 95.5},
        {"id": 2, "name": "Bob", "score": 87.0},
        {"id": 3, "name": "Charlie", "score": 72.3},
    ]


class TestExportCSV:

    def test_export_csv(self, sample_rows):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = os.path.join(tmp, "out.csv")
            DB.export_csv(sample_rows, csv_path)
            assert os.path.isfile(csv_path)

            with open(csv_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                assert len(rows) == 3
                assert rows[0]["name"] == "Alice"

    def test_export_csv_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = os.path.join(tmp, "empty.csv")
            DB.export_csv([], csv_path)
            assert os.path.isfile(csv_path)


class TestExportJSON:

    def test_export_json(self, sample_rows):
        with tempfile.TemporaryDirectory() as tmp:
            json_path = os.path.join(tmp, "out.json")
            DB.export_json(sample_rows, json_path)
            assert os.path.isfile(json_path)

            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                assert len(data) == 3
                assert data[0]["id"] == 1

    def test_export_json_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            json_path = os.path.join(tmp, "empty.json")
            DB.export_json([], json_path)
            assert os.path.isfile(json_path)
            with open(json_path, "r") as f:
                assert json.load(f) == []


class TestExportFromDB:

    def test_export_from_db_query(self):
        """从数据库查询结果直接导出"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "exp.db")
            with Connection(db_path) as conn:
                conn.execute("CREATE TABLE scores (id INTEGER, name TEXT, score REAL)")
                conn.insert_many(
                    "scores",
                    ["id", "name", "score"],
                    [[1, "Alice", 95.5], [2, "Bob", 87.0]],
                )
                rows = conn.fetchall("SELECT * FROM scores ORDER BY id")

            csv_path = os.path.join(tmp, "scores.csv")
            DB.export_csv(rows, csv_path)
            assert os.path.isfile(csv_path)

            json_path = os.path.join(tmp, "scores.json")
            DB.export_json(rows, json_path)
            assert os.path.isfile(json_path)
