import psycopg2

conn = psycopg2.connect("postgresql://postgres:data@localhost:5432/mindtrackai_db")
cur = conn.cursor()
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='baseline_surveys' ORDER BY ordinal_position")
cols = [r[0] for r in cur.fetchall()]
print("baseline_surveys columns:", cols)
conn.close()
