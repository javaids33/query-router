import unittest
from router import decide_engine

class TestRouterLogic(unittest.TestCase):
    
    def test_postgres_routing(self):
        # Transactional lookups
        self.assertEqual(decide_engine("SELECT * FROM users WHERE id = 1"), "postgres")
        self.assertEqual(decide_engine("UPDATE users SET name='Alice' WHERE id=1"), "postgres")
        self.assertEqual(decide_engine("INSERT INTO users VALUES (1, 'Bob')"), "postgres")

    def test_clickhouse_routing(self):
        # Aggregations on single table
        self.assertEqual(decide_engine("SELECT count(*) FROM users"), "clickhouse")
        self.assertEqual(decide_engine("SELECT role, SUM(orders) FROM users GROUP BY role"), "clickhouse")

    def test_trino_routing(self):
        # Joins
        self.assertEqual(decide_engine("SELECT u.name, o.id FROM users u JOIN orders o ON u.id = o.user_id"), "trino")
        
    def test_duckdb_routing(self):
        # Default / Fallback
        self.assertEqual(decide_engine("SELECT * FROM users LIMIT 10"), "duckdb")
        self.assertEqual(decide_engine("SELECT * FROM 'my_file.csv'"), "duckdb")

if __name__ == '__main__':
    unittest.main()
