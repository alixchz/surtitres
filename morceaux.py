import streamlit as st
import pandas as pd
import sqlite3
from paroles import tableur_existe, charger_paroles_depuis_tableur
from surtitres import generate_frame_title, generate_text, make_latex

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
        SELECT id, ordre, air, compositeur, annee, extrait_de 
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

def mettre_a_jour_morceau(morceau_id, ordre, air, compositeur, annee, extrait_de):
    """Mettre à jour un morceau individuel"""
    conn = sqlite3.connect('projects.db')
    c = conn.cursor()
    
    try:
        c.execute('''
            UPDATE morceaux 
            SET ordre = ?, air = ?, compositeur = ?, annee = ?, extrait_de = ?
            WHERE id = ?
        ''', (ordre, air, compositeur, annee, extrait_de, morceau_id))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Erreur lors de la mise à jour : {e}")
        return False
    finally:
        conn.close()

def ajouter_morceau(projet_id, ordre, air, compositeur, annee, extrait_de):
    """Ajouter un nouveau morceau"""
    conn = sqlite3.connect('projects.db')
    c = conn.cursor()
    
    try:
        c.execute('''
            INSERT INTO morceaux (projet_id, ordre, air, compositeur, annee, extrait_de)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (projet_id, ordre, air, compositeur, annee, extrait_de))
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
    edit_conflict = False

    st.subheader("🎵 Gestion des morceaux")
    
    # Gestion de l'édition en cours
    if 'edition_morceau_id' not in st.session_state:
        st.session_state.edition_morceau_id = None
    
    # Charger les morceaux existants
    morceaux = charger_morceaux(projet_id)
    max_ordre = get_max_ordre(projet_id)
    
    # Afficher les morceaux existants
    if morceaux:

        st.subheader("📋 Liste des morceaux (dans l'ordre)")
        col1, col2 = st.columns([0.8, 0.2])
        with col1:
            with st.expander("ℹ️ Aide concernant l'ordre"):
                st.info("Pour déplacer un morceau, modifiez son numéro (bouton ✏️). Les morceaux suivants seront décalés automatiquement. Attention, pour placer un morceau à la fin, saisissez un numéro supérieur au maximum visible. Si les numéros ne se suivent plus naturellement à partir de 1, cliquez sur le bouton 🧹 juste à droite.")       
        with col2:
            if st.button("🧹 Nettoyer l'ordre", help="Corrige la numérotation pour avoir 1, 2, 3... sans trous"):
                if nettoyer_ordre_morceaux(projet_id):
                    st.success("✅ Ordre nettoyé avec succès")
                    st.rerun()
        for morceau in morceaux:
            morceau_id, ordre, air, compositeur, annee, extrait_de = morceau
            
            # Vérifier si un tableur existe pour ce morceau
            tableur_existant = tableur_existe(morceau_id)
            statut_paroles = "✅" if tableur_existant else "❌"
            
            if st.session_state.edition_morceau_id == morceau_id:
                # Mode édition
                with st.container():
                    st.markdown("---")
                    st.write("**✏️ Édition en cours**")
                    
                    col1, col2, col3, col4, col5, col6, col7 = st.columns([0.1, 0.25, 0.2, 0.15, 0.15, 0.2, 0.15])
                    
                    with col1:
                        nouvel_ordre = st.number_input(
                            "Ordre",
                            value=ordre,
                            min_value=1,
                            max_value=max_ordre + 10,
                            key=f"edit_ordre_{morceau_id}"
                        )
                    
                    with col2:
                        nouveau_air = st.text_input(
                            "Air",
                            value=air,
                            key=f"edit_air_{morceau_id}"
                        )
                    
                    with col3:
                        nouvel_extrait_de = st.text_input(
                            "Extrait de",
                            value=extrait_de,
                            key=f"edit_extrait_de_{morceau_id}"
                        )

                    with col4:
                        nouveau_compositeur = st.text_input(
                            "Compositeur",
                            value=compositeur,
                            key=f"edit_compositeur_{morceau_id}"
                        )
                    
                    with col5:
                        nouvelle_annee = st.text_input(
                            "Année",
                            value=annee,
                            key=f"edit_annee_{morceau_id}"
                        )
                    
                    with col6:
                        if st.button("💾 Sauvegarder", key=f"save_{morceau_id}", type="primary", use_container_width=True):
                            # Validation
                            if not nouveau_air.strip():
                                st.error("L'air est obligatoire")
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
                                if mettre_a_jour_morceau(morceau_id, ordre_final, nouveau_air.strip(), nouveau_compositeur.strip(), nouvelle_annee.strip(), nouvel_extrait_de.strip()):
                                    st.session_state.edition_morceau_id = None
                                    st.success("✅ Morceau mis à jour")
                                    st.rerun()
                    with col7:
                        if st.button("❌ Annuler", key=f"cancel_{morceau_id}", use_container_width=True):
                            st.session_state.edition_morceau_id = None
                            st.rerun()
            
            else:
                # Mode affichage

                with st.container():
                    col1, col2, col3, col4, col5, col6, col7 = st.columns([0.05, 0.3, 0.2, 0.15, 0.10, 0.15, 0.15])
                    
                    with col1:
                        st.write(f"**{ordre}**")
                    
                    with col2:
                        st.write(f"**{air}**")
                    
                    with col3:
                        st.write(extrait_de if extrait_de else "-")

                    with col4:
                        st.write(compositeur if compositeur else "-")
                    
                    with col5:
                        st.write(annee if annee else "-")
                    
                    with col6:
                        col_edit, col_delete = st.columns(2)
                        
                        with col_edit:
                            if st.button("✏️", key=f"edit_btn_{morceau_id}", use_container_width=True):
                                if st.session_state.edition_morceau_id is None:
                                    st.session_state.edition_morceau_id = morceau_id
                                    st.rerun()
                                else:
                                    edit_conflict = True
                        
                        with col_delete:
                            if st.button("🗑️", key=f"delete_btn_{morceau_id}", use_container_width=True):
                                if supprimer_morceau(morceau_id):
                                    st.success("✅ Morceau supprimé")
                                    st.rerun()

                    with col7:
                        if st.button(f"📝 Texte {statut_paroles}", key=f"paroles_btn_{morceau_id}", use_container_width=True):
                            st.session_state.current_morceau_id = morceau_id
                            st.session_state.current_morceau_titre = air
                            st.rerun()

                    if edit_conflict:
                        st.warning("ℹ️ Terminez l'édition en cours avant d'en commencer une nouvelle")
    
    else:
        st.info("ℹ️ Aucun morceau pour ce projet.")
    
    # Légende
    st.caption("📝 **Légende :** ✅ = Texte saisi, ❌ = Aucun texte")

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
                help="Si l'ordre existe déjà, le nouveau morceau aura le numéro saisi et les autres morceaux seront décalés à sa suite"
            )
        
        with col2:
            nouveau_compositeur = st.text_input("Compositeur", placeholder="Nom du compositeur")
        
        with col3:
            nouvelle_annee = st.text_input("Année", placeholder="ex: 1771-1779")

        col_air, col_extrait = st.columns(2)
        with col_air:
            nouveau_air = st.text_input("Air*", placeholder="Titre du morceau sans guillemets...")

        with col_extrait:
            nouvel_extrait_de = st.text_input("Extrait de", placeholder="Air extrait de l'opéra ou du recueil (sans guillemets)...")
        
        if st.form_submit_button("➕ Ajouter le morceau", type="primary"):
            if not nouveau_air.strip():
                st.error("❌ L'air est obligatoire")
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
                nouveau_id = ajouter_morceau(projet_id, ordre_final, nouveau_air.strip(), nouveau_compositeur.strip(), nouvelle_annee.strip(), nouvel_extrait_de.strip())
                if nouveau_id:
                    st.success(f"✅ Morceau ajouté (ordre {ordre_final})")
                    st.rerun()

    # Afficher pdf
    st.markdown("---")
    st.subheader("📄 Aperçu PDF des surtitres")
   
    # Récupérer concert_frame
    concert_frame = get_concert_frame(st.session_state.project_id)

    # Interface en deux colonnes
    col1, col2, col3 = st.columns([3, 1, 3])

    with col1:
        concert_frame_edit = st.text_area(
            "Code LaTeX du premier transparent :", 
            concert_frame, 
            height=250,
            key="concert_frame_editor",
            label_visibility="collapsed"
        )

    with col2:
        st.write("")  # Espacement
        st.write("")
        
        # Bouton de sauvegarde
        if st.button("💾 Sauvegarder", use_container_width=True):
            if update_concert_frame(st.session_state.project_id, concert_frame_edit):
                st.session_state.project_data = get_project(st.session_state.project_id)
                st.success("✅ Template sauvegardé")
                st.rerun()
        
        # Bouton de réinitialisation
        if st.button("🔄 Par défaut", use_container_width=True):
            default_frame = """\\begin{frame}{}
        \\centering
        \\vspace{-2.5cm}
        Classe de chant lyrique \\\\
        \\textbf{Nom du concert}\\\\\\
        \\vskip0.2cm
        Date
        \\vskip0.2cm
    \\end{frame}"""
            if update_concert_frame(st.session_state.project_id, default_frame):
                st.session_state.project_data = get_project(st.session_state.project_id)
                st.success("✅ Template réinitialisé")
                st.rerun()
                
    latex_content = ""
    # Pourquoi je vois une liste vide ?
    for morceau_id in [m[0] for m in morceaux]:
        frame_title = generate_frame_title(morceau_id)
        texte = generate_text(charger_paroles_depuis_tableur(morceau_id))
        latex_content += frame_title + "\n" + texte + "\n"
    make_latex(concert_frame_edit + latex_content)