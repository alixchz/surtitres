import streamlit as st
import sqlite3
import datetime
import re
import pandas as pd
import io

# Fonctions pour les tableurs
def nettoyer_nom_fichier(titre):
    """Nettoyer le titre pour créer un nom de fichier valide"""
    # Remplacer les espaces et caractères spéciaux par _
    nom_clean = re.sub(r'[^\w\s-]', '', titre)
    nom_clean = re.sub(r'[-\s]+', '_', nom_clean)
    return nom_clean.strip('_').lower()

def tableur_existe(morceau_id):
    """Vérifier si un tableur existe pour ce morceau"""
    conn = sqlite3.connect('projects.db')
    c = conn.cursor()
    c.execute('SELECT id, nom_fichier, date_import FROM tableurs_paroles WHERE morceau_id = ?', (morceau_id,))
    result = c.fetchone()
    conn.close()
    return result

def sauvegarder_tableur(morceau_id, fichier_uploaded, titre_morceau):
    """Sauvegarder le tableur uploadé"""
    conn = sqlite3.connect('projects.db')
    c = conn.cursor()
    
    try:
        # Lire les données du fichier
        donnees = fichier_uploaded.getvalue()
        
        # Déterminer l'extension en fonction du type de fichier
        if fichier_uploaded.type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            extension = "xlsx"
        elif fichier_uploaded.type == "application/vnd.oasis.opendocument.spreadsheet":
            extension = "ods"
        elif fichier_uploaded.type in ["application/vnd.ms-excel", "application/xls"]:
            extension = "xls"
        else:
            # Par défaut, utiliser l'extension originale
            extension = fichier_uploaded.name.split('.')[-1] if '.' in fichier_uploaded.name else "xlsx"
        
        nom_fichier_clean = f"{nettoyer_nom_fichier(titre_morceau)}.{extension}"
        
        # Supprimer l'ancien tableur s'il existe
        c.execute('DELETE FROM tableurs_paroles WHERE morceau_id = ?', (morceau_id,))
        
        # Insérer le nouveau
        c.execute('''
            INSERT INTO tableurs_paroles (morceau_id, nom_fichier, date_import, donnees)
            VALUES (?, ?, ?, ?)
        ''', (morceau_id, nom_fichier_clean, datetime.datetime.now().isoformat(), donnees))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Erreur lors de la sauvegarde : {e}")
        return False
    finally:
        conn.close()

def charger_tableur(morceau_id):
    """Charger le tableur depuis la base de données"""
    conn = sqlite3.connect('projects.db')
    c = conn.cursor()
    c.execute('SELECT nom_fichier, donnees FROM tableurs_paroles WHERE morceau_id = ?', (morceau_id,))
    result = c.fetchone()
    conn.close()
    return result

def afficher_contenu_tableur(morceau_id):
    """Afficher le contenu du tableur sous forme de tableau"""
    tableur_data = charger_tableur(morceau_id)
    
    if tableur_data:
        nom_fichier, donnees = tableur_data
        
        try:
            # Déterminer le type de fichier basé sur l'extension
            if nom_fichier.endswith('.ods'):
                # Lire le fichier ODS
                df = pd.read_excel(io.BytesIO(donnees), engine='odf')
            else:
                # Lire les autres formats Excel
                df = pd.read_excel(io.BytesIO(donnees))
            
            # Afficher un aperçu du tableau
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )
            
            # Statistiques
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Lignes", len(df))
            with col2:
                colonnes_remplies = df.notna().sum().sum()
                st.metric("Cellules remplies", colonnes_remplies)
            with col3:
                st.metric("Colonnes", len(df.columns))
                
        except Exception as e:
            st.error(f"Erreur lors de la lecture du tableur : {e}")

def obtenir_type_mime(nom_fichier):
    """Obtenir le type MIME en fonction de l'extension du fichier"""
    if nom_fichier.endswith('.xlsx'):
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif nom_fichier.endswith('.ods'):
        return "application/vnd.oasis.opendocument.spreadsheet"
    elif nom_fichier.endswith('.xls'):
        return "application/vnd.ms-excel"
    else:
        return "application/octet-stream"

def edition_paroles_tableur(morceau_id, morceau_titre=""):
    st.subheader(f"📝 Édition des paroles - {morceau_titre}")
    
    # Bouton retour
    if st.button("← Retour à la liste des morceaux"):
        if 'current_morceau_id' in st.session_state:
            del st.session_state.current_morceau_id
        if 'current_morceau_titre' in st.session_state:
            del st.session_state.current_morceau_titre
        st.rerun()
    
    # Vérifier si un tableur existe déjà
    tableur_existant = tableur_existe(morceau_id)
    
    if tableur_existant:
        st.info(f"Dernier import : {datetime.datetime.fromisoformat(tableur_existant[2]).strftime('%d/%m/%Y %H:%M')}")
        
        # Afficher le contenu du tableur
        st.subheader("Contenu du tableur")
        afficher_contenu_tableur(morceau_id)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📤 Télécharger")
            tableur_data = charger_tableur(morceau_id)
            if tableur_data:
                nom_fichier, donnees = tableur_data
                type_mime = obtenir_type_mime(nom_fichier)
                
                st.download_button(
                    label="📥 Télécharger le tableur",
                    data=donnees,
                    file_name=nom_fichier,
                    mime=type_mime
                )
        
        with col2:
            st.subheader("🔄 Remplacer")
            with st.expander("Charger un nouveau tableur (remplacera l'existant)"):
                nouveau_tableur = st.file_uploader(
                    "Choisir un fichier tableur",
                    type=['xlsx', 'xls', 'ods'],
                    help="Formats supportés : Excel (.xlsx, .xls), OpenDocument (.ods)",
                    key=f"upload_replace_{morceau_id}"
                )
                
                if nouveau_tableur:
                    st.warning("⚠️ **Attention** : Cela va remplacer le tableur existant !")
                    cola, colb = st.columns(2)
                    with cola:
                        if st.button("✅ Confirmer le remplacement", type="primary"):
                            if sauvegarder_tableur(morceau_id, nouveau_tableur, morceau_titre):
                                st.success("Tableur remplacé avec succès !")
                                st.rerun()
                    with colb:
                        if st.button("❌ Annuler"):
                            st.rerun()
    
    else:
        st.info("ℹ️ Aucun tableur n'a été importé pour ce morceau.")
        st.subheader("📤 Premier import")
        
        fichier_upload = st.file_uploader(
            "Charger un tableur avec les paroles",
            type=['xlsx', 'xls', 'ods'],
            help="Formats supportés : Excel (.xlsx, .xls), OpenDocument (.ods). Le fichier sera renommé automatiquement selon le titre du morceau",
            key=f"upload_new_{morceau_id}"
        )
        
        if fichier_upload:
            st.info(f"Fichier sélectionné : {fichier_upload.name} ({fichier_upload.type})")
            if st.button("💾 Sauvegarder le tableur", type="primary"):
                if sauvegarder_tableur(morceau_id, fichier_upload, morceau_titre):
                    st.success("Tableur importé avec succès !")
                    st.rerun()