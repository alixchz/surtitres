import sqlite3
import datetime
import re

# Vérifier si un projet existe
def project_exists(project_id):
    conn = sqlite3.connect('projects.db')
    c = conn.cursor()
    c.execute('SELECT id FROM projects WHERE id = ?', (project_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

# Créer un nouveau projet
def create_project(project_id, creator, description):
    conn = sqlite3.connect('projects.db')
    c = conn.cursor()
    current_time = datetime.datetime.now().isoformat()
    c.execute('''
        INSERT INTO projects (id, created_date, modified_date, creator, description)
        VALUES (?, ?, ?, ?, ?)
    ''', (project_id, current_time, current_time, creator, description))
    conn.commit()
    conn.close()

# Récupérer les informations d'un projet
def get_project(project_id):
    conn = sqlite3.connect('projects.db')
    c = conn.cursor()
    c.execute('SELECT * FROM projects WHERE id = ?', (project_id,))
    result = c.fetchone()
    conn.close()
    return result

# Valider le format de l'ID
def is_valid_project_id(project_id):
    if len(project_id) < 6:
        return False, "L'identifiant doit contenir au moins 6 caractères"
    
    # Vérifier que l'ID contient seulement des lettres, chiffres et underscores
    if not re.match(r'^[a-zA-Z0-9_]+$', project_id):
        return False, "L'identifiant ne peut contenir que des lettres (sans accents), chiffres et underscores (_)"
    
    return True, ""