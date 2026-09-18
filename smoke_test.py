from app.database import initialize_database, query

n = initialize_database()
print('Rows loaded:', n)
print('Open tickets:', query("SELECT COUNT(*) AS count FROM support_tickets WHERE status='Open'")[0]['count'])
print('Rows:', query('SELECT COUNT(*) AS count FROM support_tickets')[0]['count'])
