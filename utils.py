import sqlite3

default_concert_frame = """\\begin{frame}{}
    \\centering
    \\vspace{-2.5cm}
    Classe de chant lyrique \\\\
    \\textbf{Nom du concert}\\\\\\
    \\vskip0.2cm
    Date
    \\vskip0.2cm
\\end{frame}"""

# Initialisation de la base de données
def init_databases():
    conn = sqlite3.connect('projects.db')
    c = conn.cursor()
    
    # Table projects (existante)
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            created_date TEXT,
            modified_date TEXT,
            creator TEXT,
            description TEXT,
            concert_frame TEXT DEFAULT '{default_concert_frame}'
        )
    ''')
    
    # Table morceaux 
    c.execute('''
        CREATE TABLE IF NOT EXISTS morceaux (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            projet_id TEXT,
            ordre INTEGER,
            air TEXT,
            extrait_de TEXT,
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