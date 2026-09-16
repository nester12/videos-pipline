import sqlite3


def derive_category_weights(db_path: str) -> dict[str,float]:
    try: con=sqlite3.connect(db_path)
    except Exception: return {}
    try:
        rows=con.execute('SELECT category,views,likes,comments,shares FROM posts').fetchall()
    except sqlite3.OperationalError:
        con.close(); return {}
    con.close()
    by={}
    for cat,views,likes,comments,shares in rows:
        views=max(int(views),1)
        score=(int(likes)+2*int(comments)+3*int(shares))/views
        by.setdefault(cat,[]).append(score)
    if not by: return {}
    means={k:sum(v)/len(v) for k,v in by.items()}
    base=sum(means.values())/len(means) or 1
    return {k:round(max(0.65,min(1.5,1+(v-base)*3)),3) for k,v in means.items()}
