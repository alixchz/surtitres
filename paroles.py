import streamlit as st
import sqlite3
import datetime
import re
import pandas as pd
import io
from surtitres import generate_frame_title, generate_text, make_latex
from morceaux_back import get_morceau, mettre_a_jour_morceau

# Constante pour la limite de caractères
NB_CAR_MAX = 70

# Fonctions pour les tableurs
def nettoyer_nom_fichier(air):
    """Nettoyer le nom de l'air pour créer un nom de fichier valide"""
    nom_clean = re.sub(r'[^\w\s-]', '', air)
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

def sauvegarder_tableur(morceau_id, fichier_uploaded, titre_air):
    """Sauvegarder le tableur uploadé"""
    conn = sqlite3.connect('projects.db')
    c = conn.cursor()
    
    try:
        donnees = fichier_uploaded.getvalue()
        
        if fichier_uploaded.type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            extension = "xlsx"
        elif fichier_uploaded.type == "application/vnd.oasis.opendocument.spreadsheet":
            extension = "ods"
        elif fichier_uploaded.type in ["application/vnd.ms-excel", "application/xls"]:
            extension = "xls"
        else:
            extension = fichier_uploaded.name.split('.')[-1] if '.' in fichier_uploaded.name else "xlsx"
        
        nom_fichier_clean = f"{nettoyer_nom_fichier(titre_air)}.{extension}"
        
        c.execute('DELETE FROM tableurs_paroles WHERE morceau_id = ?', (morceau_id,))
        
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

def charger_paroles_depuis_tableur(morceau_id):
    """Charger le texte depuis le tableur sous forme de DataFrame"""
    tableur_data = charger_tableur(morceau_id)
    
    if tableur_data:
        nom_fichier, donnees = tableur_data
        
        try:
            if nom_fichier.endswith('.ods'):
                df = pd.read_excel(io.BytesIO(donnees), engine='odf')
            else:
                df = pd.read_excel(io.BytesIO(donnees))
            
            # Assurer que nous avons les bonnes colonnes
            if len(df.columns) < 2:
                df = pd.DataFrame(columns=['Original', 'Traduction'])
            elif len(df.columns) > 2:
                df = df.iloc[:, :2]  # Prendre seulement les 2 premières colonnes
                df.columns = ['Original', 'Traduction']
            else:
                df.columns = ['Original', 'Traduction']
                
            return df
        except Exception as e:
            st.error(f"Erreur lors de la lecture du tableur : {e}")
            return pd.DataFrame(columns=['Original', 'Traduction'])
    
    return pd.DataFrame(columns=['Original', 'Traduction'])

def sauvegarder_paroles_vers_tableur(morceau_id, df, titre_air):
    """Sauvegarder le DataFrame vers le tableur"""
    try:
        # Créer un fichier Excel en mémoire
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Texte')
        
        # Créer un fichier uploadé simulé
        class FakeUploadedFile:
            def __init__(self, data, filename):
                self.data = data
                self.name = filename
                self.type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            
            def getvalue(self):
                return self.data
        
        fake_file = FakeUploadedFile(output.getvalue(), f"{nettoyer_nom_fichier(titre_air)}.xlsx")
        
        return sauvegarder_tableur(morceau_id, fake_file, titre_air)
        
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde du texte : {e}")
        return False

def afficher_contenu_tableur(morceau_id):
    """Afficher le contenu du tableur sous forme de tableau"""
    tableur_data = charger_tableur(morceau_id)
    
    if tableur_data:
        nom_fichier, donnees = tableur_data
        
        try:
            if nom_fichier.endswith('.ods'):
                df = pd.read_excel(io.BytesIO(donnees), engine='odf')
            else:
                df = pd.read_excel(io.BytesIO(donnees))
            
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )
                
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
    # Bouton retour
    if st.button("↩️ Retour à la liste des morceaux"):
        if 'current_morceau_id' in st.session_state:
            del st.session_state.current_morceau_id
        if 'current_morceau_titre' in st.session_state:
            del st.session_state.current_morceau_titre
        if 'edition_ligne_index' in st.session_state:
            del st.session_state.edition_ligne_index
        st.rerun()
    
    _, ordre, morceau_titre, compositeur, annee, extrait_de, text_status = get_morceau(morceau_id)

    st.subheader(f"📝 Édition du texte - {morceau_titre}")
    
    # Gestion du mode édition
    if 'edition_ligne_index' not in st.session_state:
        st.session_state.edition_ligne_index = None
    
    # Charger les paroles
    df_paroles = charger_paroles_depuis_tableur(morceau_id)
    
    # Vérifier si un tableur existe déjà
    tableur_existant = tableur_existe(morceau_id)
    
    # MODIFICATION : Vérifier aussi si on a des données dans le DataFrame
    has_paroles_data = len(df_paroles) > 0
    
    if tableur_existant or has_paroles_data:
        if tableur_existant:
            col_statut, col_derniere_modif, _ = st.columns([2, 2, 6])
            with col_statut:
                helper_status = {
                    "🔴 Aucun texte saisi":'not_started', 
                    "🟠 Texte saisi, à vérifier":"draft",
                    "🟢 Texte validé":'validated'
                }

                def status_change():
                    nonlocal nouveau_status
                    nouveau_status = helper_status[st.session_state[f"select_status_{morceau_id}"]]
                    mettre_a_jour_morceau(morceau_id, ordre, morceau_titre, compositeur, annee, extrait_de, nouveau_status)

                nouveau_status = st.selectbox(
                    "Avancement",
                    options=list(helper_status.keys()),
                    index=list(helper_status.values()).index(text_status),
                    key=f"select_status_{morceau_id}",
                    on_change=status_change)

                
            with col_derniere_modif:
                st.info(f"Dernière modification : {datetime.datetime.fromisoformat(tableur_existant[2]).strftime('%d/%m/%Y %H:%M')}")
        else:
            st.info("Tableur vide créé - prêt à être édité")

        # Section téléchargement/remplacement 
        st.subheader("📊 Vue d'ensemble sous forme de tableur")
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
        st.markdown("---")

        # Mode édition détaillée
        st.subheader("✏️ Édition détaillée du texte")
        
        # Afficher toutes les lignes avec possibilité d'édition
        for index, row in df_paroles.iterrows():
            with st.container():
                if st.session_state.edition_ligne_index == index:
                    # Mode édition de la ligne
                    st.write(f"**Édition de la ligne {index + 1}**")
                    
                    col1, col2, col3 = st.columns([0.45, 0.45, 0.1])
                    
                    with col1:
                        nouveau_original = st.text_area(
                            "Version originale",
                            value=row['Original'] if pd.notna(row['Original']) else "",
                            height=50,
                            key=f"edit_orig_{index}",
                            max_chars=NB_CAR_MAX
                        )
                        if len(nouveau_original) > NB_CAR_MAX:
                            st.warning(f"⚠️ {len(nouveau_original)}/{NB_CAR_MAX} caractères")
                    
                    with col2:
                        nouvelle_traduction = st.text_area(
                            "Traduction",
                            value=row['Traduction'] if pd.notna(row['Traduction']) else "",
                            height=50,
                            key=f"edit_trad_{index}",
                            max_chars=NB_CAR_MAX
                        )
                        if len(nouvelle_traduction) > NB_CAR_MAX:
                            st.warning(f"⚠️ {len(nouvelle_traduction)}/{NB_CAR_MAX} caractères")
                    
                    with col3:
                        st.write("")  # Espacement
                        st.write("")
                        
                        # Boutons d'action pour l'édition
                        if st.button("💾", key=f"save_line_{index}", help="Sauvegarder cette ligne"):
                            # Mettre à jour la ligne
                            df_paroles.at[index, 'Original'] = nouveau_original
                            df_paroles.at[index, 'Traduction'] = nouvelle_traduction
                            
                            # Sauvegarder tout le tableur
                            if sauvegarder_paroles_vers_tableur(morceau_id, df_paroles, morceau_titre):
                                st.session_state.edition_ligne_index = None
                                st.success("✅ Ligne sauvegardée")
                                st.rerun()
                        
                        if st.button("❌", key=f"cancel_line_{index}", help="Annuler"):
                            st.session_state.edition_ligne_index = None
                            st.rerun()
                else:
                    # Mode affichage de la ligne
                    col1, col2, col3, col4, col5 = st.columns([0.39, 0.39, 0.066, 0.066, 0.066])
                    
                    with col1:
                        st.text_area(
                            "Version originale",
                            value=row['Original'] if pd.notna(row['Original']) else "",
                            height=50,
                            key=f"display_orig_{index}",
                            disabled=True,
                            label_visibility="collapsed"
                        )
                    
                    with col2:
                        st.text_area(
                            "Traduction",
                            value=row['Traduction'] if pd.notna(row['Traduction']) else "",
                            height=50,
                            key=f"display_trad_{index}",
                            disabled=True,
                            label_visibility="collapsed"
                        )
                    
                    with col3:
                        # Bouton pour éditer cette ligne
                        if st.button("✏️", key=f"edit_{index}", help="Éditer cette ligne"):
                            st.session_state.edition_ligne_index = index
                            st.rerun()

                    with col4:
                        if st.button("➕", key=f"insert_after_{index}", help="Insérer une ligne vide après"):
                            # Créer une nouvelle ligne vide
                            nouvelle_ligne = pd.DataFrame({
                                'Original': [''],
                                'Traduction': ['']
                            })
                            
                            # Insérer après l'index actuel
                            df_part1 = df_paroles.iloc[:index+1]
                            df_part2 = df_paroles.iloc[index+1:]
                            df_paroles = pd.concat([df_part1, nouvelle_ligne, df_part2], ignore_index=True)
                            
                            # Sauvegarder
                            if sauvegarder_paroles_vers_tableur(morceau_id, df_paroles, morceau_titre):
                                st.session_state.edition_ligne_index = index + 1  # Éditer la nouvelle ligne
                                st.success("✅ Ligne vide insérée")
                                st.rerun()
                    with col5:
                        if st.button("🗑️", key=f"delete_line_{index}", help="Supprimer cette ligne"):
                            # Supprimer la ligne
                            df_paroles = df_paroles.drop(index).reset_index(drop=True)
                            
                            # Sauvegarder
                            if sauvegarder_paroles_vers_tableur(morceau_id, df_paroles, morceau_titre):
                                st.session_state.edition_ligne_index = None
                                st.success("✅ Ligne supprimée")
                                st.rerun()
            
            #st.markdown("---")
        
        # Bouton pour ajouter une ligne à la fin
        if st.button("➕ Ajouter une ligne à la fin", type="secondary"):
            nouvelle_ligne = pd.DataFrame({
                'Original': [''],
                'Traduction': ['']
            })
            df_paroles = pd.concat([df_paroles, nouvelle_ligne], ignore_index=True)
            
            if sauvegarder_paroles_vers_tableur(morceau_id, df_paroles, morceau_titre):
                st.session_state.edition_ligne_index = len(df_paroles) - 1
                st.success("✅ Nouvelle ligne ajoutée")
                st.rerun()
        
        st.markdown("---")
        st.subheader("Tester le rendu final")
        content = generate_frame_title(morceau_id) + generate_text(df_paroles)
        make_latex(content)

    else:
        st.info("ℹ️ Aucun tableur n'a été importé pour ce morceau.")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📤 Importer un tableur")
            
            fichier_upload = st.file_uploader(
                "Charger un tableur avec le texte (original à gauche, traduction à droite)",
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

        with col2:
            # Proposer de créer un tableur vide avec 3 lignes
            st.subheader("➕ Créer un tableur vide")
            if st.button("Créer un tableur vide", type="primary"):
                # Créer un DataFrame vide avec les bonnes colonnes
                df_vide = pd.DataFrame(columns=['Original', 'Traduction'])
                for i in range(3):
                    df_vide = pd.concat([df_vide, pd.DataFrame({'Original': [f'Texte original {i}'], 'Traduction': [f'Texte traduit {i}']})], ignore_index=True)
                if sauvegarder_paroles_vers_tableur(morceau_id, df_vide, morceau_titre):
                    st.success("Tableur vide créé avec succès !")
                    st.rerun()