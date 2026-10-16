import sqlite3

def init_db():
    conn = sqlite3.connect('users.db')
    curr = conn.cursor()
    # Таблица клиентов
    curr.execute('''CREATE TABLE IF NOT EXISTS clients 
                 (id INTEGER PRIMARY KEY, name TEXT, ai_mode INTEGER DEFAULT 1, scenario TEXT DEFAULT 'reactivation')''')
    conn.commit()
    conn.close()

def set_ai_mode(client_id, mode: int):
    conn = sqlite3.connect('users.db')
    conn.execute("UPDATE clients SET ai_mode = ? WHERE id = ?", (mode, client_id))
    conn.commit()
    conn.close()

def update_scenario(client_id, scenario: str):
    conn = sqlite3.connect('users.db')
    conn.execute("UPDATE clients SET scenario = ? WHERE id = ?", (scenario, client_id))
    conn.commit()
    conn.close()

def get_client_info(client_id):
    conn = sqlite3.connect('users.db')
    res = conn.execute("SELECT ai_mode, name, scenario FROM clients WHERE id = ?", (client_id,)).fetchone()
    conn.close()
    if res:
        return res
    else:
        # Если клиента нет, создаем его
        conn = sqlite3.connect('users.db')
        conn.execute("INSERT INTO clients (id, name) VALUES (?, ?)", (client_id, "Новый клиент"))
        conn.commit()
        return (1, "Новый клиент", "reactivation")