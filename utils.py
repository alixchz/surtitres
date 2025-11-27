import sqlite3

# Initialisation de la base de données
def init_databases():
    conn = sqlite3.connect('projects.db')
    c = conn.cursor()
    
    # Table projects (existante)
    c.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            created_date TEXT,
            modified_date TEXT,
            creator TEXT,
            description TEXT
        )
    ''')
    
    # Table morceaux (simplifiée)
    c.execute('''
        CREATE TABLE IF NOT EXISTS morceaux (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            projet_id TEXT,
            ordre INTEGER,
            titre TEXT,
            compositeur TEXT,
            annee TEXT,
            FOREIGN KEY (projet_id) REFERENCES projects (id)
        )
    ''')
    
    # Table pour stocker les fichiers tableur
    c.execute('''
        CREATE TABLE IF NOT EXISTS tableurs_paroles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            morceau_id INTEGER,
            nom_fichier TEXT,
            date_import TEXT,
            donnees BLOB,
            FOREIGN KEY (morceau_id) REFERENCES morceaux (id)
        )
    ''')
    
    conn.commit()
    conn.close()