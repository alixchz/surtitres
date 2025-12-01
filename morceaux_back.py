import sqlite3
import streamlit as st

def get_concert_frame(project_id):
    """Récupérer le concert_frame d'un projet"""
    conn = sqlite3.connect('projects.db')
    c = conn.cursor()
    c.execute('SELECT concert_frame FROM projects WHERE id = ?', (project_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else ""

def update_concert_frame(project_id, new_concert_frame):
    """Mettre à jour le concert_frame d'un projet"""
    conn = sqlite3.connect('projects.db')
    c = conn.cursor()
    c.execute('UPDATE projects SET concert_frame = ? WHERE id = ?', (new_concert_frame, project_id))
    conn.commit()
    conn.close()
    return True

def get_project(project_id):
    conn = sqlite3.connect('projects.db')
    c = conn.cursor()
    c.execute('SELECT * FROM projects WHERE id = ?', (project_id,))
    result = c.fetchone()
    conn.close()
    return result  # Doit retourner (id, created_date, modified_date, creator, description, concert_frame)

def charger_morceaux(projet_id):
    conn = sqlite3.connect('projects.db')
    c = conn.cursor()
    c.execute('''
        SELECT id, ordre, air, compositeur, annee, extrait_de, text_status 
        FROM morceaux 
        WHERE projet_id = ? 
        ORDER BY ordre
    ''', (projet_id,))
    result = c.fetchall()
    conn.close()
    return result

def get_max_ordre(projet_id):
    """Récupérer le numéro d'ordre maximum"""
    conn = sqlite3.connect('projects.db')
    c = conn.cursor()
    c.execute('SELECT MAX(ordre) FROM morceaux WHERE projet_id = ?', (projet_id,))
    result = c.fetchone()[0] or 0
    conn.close()
    return result

def ordre_existe(projet_id, ordre, morceau_id_actuel=None):
    """Vérifier si un numéro d'ordre existe déjà"""
    conn = sqlite3.connect('projects.db')
    c = conn.cursor()
    if morceau_id_actuel:
        c.execute('SELECT id FROM morceaux WHERE projet_id = ? AND ordre = ? AND id != ?', 
                 (projet_id, ordre, morceau_id_actuel))
    else:
        c.execute('SELECT id FROM morceaux WHERE projet_id = ? AND ordre = ?', 
                 (projet_id, ordre))
    result = c.fetchone() is not None
    conn.close()
    return result

def nettoyer_ordre_morceaux(projet_id):
    """Réorganise l'ordre des morceaux pour avoir une suite incrémentée de 1"""
    conn = sqlite3.connect('projects.db')
    c = conn.cursor()
    
    try:
        # Récupérer tous les morceaux triés par ordre actuel
        c.execute('''
            SELECT id, ordre, air 
            FROM morceaux 
            WHERE projet_id = ? 
            ORDER BY ordre, id
        ''', (projet_id,))
        morceaux = c.fetchall()
        
        if not morceaux:
            return True
            
        # Mettre à jour l'ordre de façon séquentielle
        for nouvel_ordre, (morceau_id, ancien_ordre, air) in enumerate(morceaux, 1):
            c.execute('UPDATE morceaux SET ordre = ? WHERE id = ?', (nouvel_ordre, morceau_id))
        
        conn.commit()
        return True
        
    except Exception as e:
        conn.rollback()
        st.error(f"Erreur lors du nettoyage de l'ordre : {e}")
        return False
    finally:
        conn.close()

def decaler_ordres(projet_id, ordre_depuis):
    """Décaler tous les ordres à partir d'un certain numéro"""
    conn = sqlite3.connect('projects.db')
    c = conn.cursor()
    c.execute('''
        UPDATE morceaux 
        SET ordre = ordre + 1 
        WHERE projet_id = ? AND ordre >= ?
    ''', (projet_id, ordre_depuis))
    conn.commit()
    conn.close()

def mettre_a_jour_morceau(morceau_id, ordre, air, compositeur, annee, extrait_de, text_status):
    """Mettre à jour un morceau individuel"""
    conn = sqlite3.connect('projects.db')
    c = conn.cursor()
    
    try:
        c.execute('''
            UPDATE morceaux 
            SET ordre = ?, air = ?, compositeur = ?, annee = ?, extrait_de = ?, text_status = ?
            WHERE id = ?
        ''', (ordre, air, compositeur, annee, extrait_de, text_status, morceau_id))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Erreur lors de la mise à jour : {e}")
        return False
    finally:
        conn.close()

def ajouter_morceau(projet_id, ordre, air, compositeur, annee, extrait_de, text_status='not_started'):
    """Ajouter un nouveau morceau"""
    conn = sqlite3.connect('projects.db')
    c = conn.cursor()
    
    try:
        c.execute('''
            INSERT INTO morceaux (projet_id, ordre, air, compositeur, annee, extrait_de, text_status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (projet_id, ordre, air, compositeur, annee, extrait_de, text_status))
        conn.commit()
        return c.lastrowid
    except Exception as e:
        conn.rollback()
        st.error(f"Erreur lors de l'ajout : {e}")
        return None
    finally:
        conn.close()

def supprimer_morceau(morceau_id):
    """Supprimer un morceau"""
    conn = sqlite3.connect('projects.db')
    c = conn.cursor()
    
    try:
        # Supprimer d'abord les tableurs associés
        c.execute('DELETE FROM tableurs_paroles WHERE morceau_id = ?', (morceau_id,))
        # Puis supprimer le morceau
        c.execute('DELETE FROM morceaux WHERE id = ?', (morceau_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Erreur lors de la suppression : {e}")
        return False
    finally:
        conn.close()

def get_morceau(morceau_id):
    conn = sqlite3.connect('projects.db')
    c = conn.cursor()
    c.execute('''
        SELECT id, ordre, air, compositeur, annee, extrait_de, text_status 
        FROM morceaux 
        WHERE id = ? 
        ORDER BY ordre
    ''', (morceau_id,))
    result = c.fetchall()
    conn.close()
    return result[0]