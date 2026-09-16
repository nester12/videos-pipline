import sqlite3

SCHEMA='''CREATE TABLE IF NOT EXISTS posts (post_id TEXT PRIMARY KEY, category TEXT NOT NULL, views INTEGER NOT NULL, likes INTEGER NOT NULL, comments INTEGER NOT NULL, shares INTEGER NOT NULL)'''


def record_post_metrics(db_path: str, row: dict) -> None:
    with sqlite3.connect(db_path) as con:
        con.execute(SCHEMA)
        con.execute('''INSERT INTO posts(post_id,category,views,likes,comments,shares) VALUES(?,?,?,?,?,?) ON CONFLICT(post_id) DO UPDATE SET category=excluded.category,views=excluded.views,likes=excluded.likes,comments=excluded.comments,shares=excluded.shares''', (str(row['post_id']),str(row['category']),int(row.get('views',0)),int(row.get('likes',0)),int(row.get('comments',0)),int(row.get('shares',0))))
        con.commit()
