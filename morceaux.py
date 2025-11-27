import streamlit as st
import pandas as pd
import sqlite3
from paroles import tableur_existe

def charger_morceaux(projet_id):
    conn = sqlite3.connect('projects.db')
    c = conn.cursor()
    c.execute('''
        SELECT id, ordre, titre, compositeur, annee 
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

def mettre_a_jour_morceau(morceau_id, ordre, titre, compositeur, annee):
    """Mettre à jour un morceau individuel"""
    conn = sqlite3.connect('projects.db')
    c = conn.cursor()
    
    try:
        c.execute('''
            UPDATE morceaux 
            SET ordre = ?, titre = ?, compositeur = ?, annee = ?
            WHERE id = ?
        ''', (ordre, titre, compositeur, annee, morceau_id))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Erreur lors de la mise à jour : {e}")
        return False
    finally:
        conn.close()

def ajouter_morceau(projet_id, ordre, titre, compositeur, annee):
    """Ajouter un nouveau morceau"""
    conn = sqlite3.connect('projects.db')
    c = conn.cursor()
    
    try:
        c.execute('''
            INSERT INTO morceaux (projet_id, ordre, titre, compositeur, annee)
            VALUES (?, ?, ?, ?, ?)
        ''', (projet_id, ordre, titre, compositeur, annee))
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

def gestion_morceaux(projet_id):
    st.subheader("🎵 Gestion des morceaux")
    
    # Gestion de l'édition en cours
    if 'edition_morceau_id' not in st.session_state:
        st.session_state.edition_morceau_id = None
    
    # Charger les morceaux existants
    morceaux = charger_morceaux(projet_id)
    max_ordre = get_max_ordre(projet_id)
    
    # Afficher les morceaux existants
    if morceaux:
        st.subheader("📋 Liste des morceaux")
        
        for morceau in morceaux:
            morceau_id, ordre, titre, compositeur, annee = morceau
            
            # Vérifier si un tableur existe pour ce morceau
            tableur_existant = tableur_existe(morceau_id)
            statut_paroles = "✅" if tableur_existant else "❌"
            
            if st.session_state.edition_morceau_id == morceau_id:
                # Mode édition
                with st.container():
                    st.markdown("---")
                    st.write("**✏️ Édition en cours**")
                    
                    col1, col2, col3, col4, col5, col6 = st.columns([0.1, 0.25, 0.15, 0.15, 0.2, 0.15])
                    
                    with col1:
                        nouvel_ordre = st.number_input(
                            "Ordre",
                            value=ordre,
                            min_value=1,
                            max_value=max_ordre + 10,
                            key=f"edit_ordre_{morceau_id}"
                        )
                    
                    with col2:
                        nouveau_titre = st.text_input(
                            "Titre",
                            value=titre,
                            key=f"edit_titre_{morceau_id}"
                        )
                    
                    with col3:
                        nouveau_compositeur = st.text_input(
                            "Compositeur",
                            value=compositeur,
                            key=f"edit_compositeur_{morceau_id}"
                        )
                    
                    with col4:
                        nouvelle_annee = st.text_input(
                            "Année",
                            value=annee,
                            key=f"edit_annee_{morceau_id}"
                        )
                    
                    with col5:
                        if st.button("💾 Sauvegarder", key=f"save_{morceau_id}", type="primary", use_container_width=True):
                            # Validation
                            if not nouveau_titre.strip():
                                st.error("Le titre est obligatoire")
                            else:
                                # Gestion des conflits d'ordre
                                ordre_final = nouvel_ordre
                                if ordre_existe(projet_id, nouvel_ordre, morceau_id):
                                    # Décaler les ordres
                                    decaler_ordres(projet_id, nouvel_ordre)
                                    st.info(f"⚠️ Ordre décalé à partir de {nouvel_ordre}")
                                
                                # Limiter l'ordre maximum
                                if ordre_final > max_ordre + 1:
                                    ordre_final = max_ordre + 1
                                    st.info(f"⚠️ Ordre limité à {ordre_final}")
                                
                                # Sauvegarder
                                if mettre_a_jour_morceau(morceau_id, ordre_final, nouveau_titre.strip(), nouveau_compositeur.strip(), nouvelle_annee.strip()):
                                    st.session_state.edition_morceau_id = None
                                    st.success("✅ Morceau mis à jour")
                                    st.rerun()
                    with col6:
                        if st.button("❌ Annuler", key=f"cancel_{morceau_id}", use_container_width=True):
                            st.session_state.edition_morceau_id = None
                            st.rerun()
            
            else:
                # Mode affichage
                with st.container():
                    st.markdown("---")
                    col1, col2, col3, col4, col5, col6 = st.columns([0.1, 0.25, 0.15, 0.15, 0.2, 0.15])
                    
                    with col1:
                        st.write(f"**{ordre}**")
                    
                    with col2:
                        st.write(f"**{titre}**")
                    
                    with col3:
                        st.write(compositeur if compositeur else "-")
                    
                    with col4:
                        st.write(annee if annee else "-")
                    
                    with col5:
                        # Groupe statut + bouton paroles
                        col_statut, col_paroles = st.columns([0.3, 0.7])
                        with col_statut:
                            st.write(statut_paroles)
                        with col_paroles:
                            if st.button("📝 Paroles", key=f"paroles_btn_{morceau_id}", use_container_width=True):
                                st.session_state.current_morceau_id = morceau_id
                                st.session_state.current_morceau_titre = titre
                                st.rerun()
                    
                    with col6:
                        # Boutons d'action côte à côte
                        col_edit, col_delete = st.columns(2)
                        
                        with col_edit:
                            if st.button("✏️", key=f"edit_btn_{morceau_id}", use_container_width=True):
                                if st.session_state.edition_morceau_id is None:
                                    st.session_state.edition_morceau_id = morceau_id
                                    st.rerun()
                                else:
                                    st.warning("ℹ️ Terminez l'édition en cours avant d'en commencer une nouvelle")
                        
                        with col_delete:
                            if st.button("🗑️", key=f"delete_btn_{morceau_id}", use_container_width=True):
                                if supprimer_morceau(morceau_id):
                                    st.success("✅ Morceau supprimé")
                                    st.rerun()
    
    else:
        st.info("ℹ️ Aucun morceau pour ce projet.")
    
    # Ajout d'un nouveau morceau
    st.markdown("---")
    st.subheader("➕ Ajouter un nouveau morceau")
    
    with st.form("nouveau_morceau"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            nouvel_ordre = st.number_input(
                "Ordre*",
                min_value=1,
                max_value=max_ordre + 10,
                value=max_ordre + 1,
                help="Si l'ordre existe déjà, les morceaux seront décalés"
            )
        
        with col2:
            nouveau_compositeur = st.text_input("Compositeur", placeholder="Nom du compositeur")
        
        with col3:
            nouvelle_annee = st.text_input("Année", placeholder="ex: 1771-1779")

        nouveau_titre = st.text_input("Titre*", placeholder="Titre du morceau")
        
        if st.form_submit_button("➕ Ajouter le morceau", type="primary"):
            if not nouveau_titre.strip():
                st.error("❌ Le titre est obligatoire")
            else:
                # Gestion des conflits d'ordre
                ordre_final = nouvel_ordre
                if ordre_existe(projet_id, nouvel_ordre):
                    # Décaler les ordres
                    decaler_ordres(projet_id, nouvel_ordre)
                    st.info(f"⚠️ Ordres décalés à partir de {nouvel_ordre}")
                
                # Limiter l'ordre maximum
                if ordre_final > max_ordre + 1:
                    ordre_final = max_ordre + 1
                    st.info(f"⚠️ Ordre limité à {ordre_final}")
                
                # Ajouter le morceau
                nouveau_id = ajouter_morceau(projet_id, ordre_final, nouveau_titre.strip(), nouveau_compositeur.strip(), nouvelle_annee.strip())
                if nouveau_id:
                    st.success(f"✅ Morceau ajouté (ordre {ordre_final})")
                    st.rerun()
    
    # Légende
    st.caption("📝 **Légende :** ✅ = Tableur de paroles existant, ❌ = Aucun tableur")