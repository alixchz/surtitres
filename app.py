import streamlit as st
import datetime
from projets import project_exists, create_project, get_project, is_valid_project_id
from morceaux import gestion_morceaux
from paroles import edition_paroles_tableur
from utils import init_databases

# Configuration de la page
st.set_page_config(
    page_title="Gestion de Projets",
    page_icon="📁",
    layout="wide"
)

# Initialiser la base de données
init_databases()

# Récupérer le projet depuis les query parameters
def get_project_from_query_params():
    """Récupérer l'ID du projet depuis les query parameters"""
    try:
        # Essayer la nouvelle API (Streamlit >= 1.24.0)
        if hasattr(st, 'query_params'):
            query_params = st.query_params
            project_id = query_params.get("project", None)
            return project_id
        else:
            # Ancienne API (Streamlit < 1.24.0)
            query_params = st.experimental_get_query_params()
            project_id = query_params.get("project", [None])[0]
            return project_id
    except Exception as e:
        st.error(f"Erreur lors de la récupération des paramètres: {e}")
        return None

def set_project_to_query_params(project_id):
    """Définir l'ID du projet dans les query parameters"""
    try:
        if hasattr(st, 'query_params'):
            # Nouvelle API
            if project_id:
                st.query_params["project"] = project_id
            else:
                if "project" in st.query_params:
                    del st.query_params["project"]
        else:
            # Ancienne API
            if project_id:
                st.experimental_set_query_params(project=project_id)
            else:
                st.experimental_set_query_params()
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde des paramètres: {e}")

# Initialiser l'état de session depuis les query parameters
if 'project_id' not in st.session_state:
    st.session_state.project_id = None
    st.session_state.project_data = None
    
    # Essayer de récupérer depuis les query params
    project_id_from_params = get_project_from_query_params()
    
    if project_id_from_params:
        if project_exists(project_id_from_params):
            st.session_state.project_id = project_id_from_params
            st.session_state.project_data = get_project(project_id_from_params)
        else:
            # Nettoyer les paramètres si le projet n'existe pas
            set_project_to_query_params(None)

# Page d'accueil - Sélection/Création de projet
if st.session_state.project_id is None:
    st.title("📁 Gestion de Projets")
    st.markdown("---")
    
    # Afficher un message si on vient de quitter un projet
    if 'just_left_project' in st.session_state:
        st.info("👋 Vous avez quitté le projet. Choisissez un nouveau projet ou créez-en un.")
        del st.session_state.just_left_project
    
    # Onglets pour choisir entre rejoindre ou créer un projet
    tab1, tab2 = st.tabs(["Rejoindre un projet existant", "Créer un nouveau projet"])
    
    with tab1:
        st.subheader("Rejoindre un projet")
        existing_id = st.text_input("Identifiant du projet", placeholder="Entrez l'ID du projet...", key="join_id")
        
        if st.button("Rejoindre le projet", type="primary", key="join_btn"):
            if existing_id:
                is_valid, error_msg = is_valid_project_id(existing_id)
                if is_valid:
                    if project_exists(existing_id):
                        st.session_state.project_id = existing_id
                        st.session_state.project_data = get_project(existing_id)
                        # Sauvegarder dans les query params
                        set_project_to_query_params(existing_id)
                        st.rerun()
                    else:
                        st.error("❌ Projet non trouvé. Vérifiez l'identifiant.")
                else:
                    st.error(f"❌ {error_msg}")
            else:
                st.warning("⚠️ Veuillez saisir un identifiant.")
    
    with tab2:
        st.subheader("Créer un nouveau projet")
        
        new_id = st.text_input(
            "Identifiant du projet", 
            placeholder="6 caractères minimum (lettres, chiffres, _ uniquement)",
            key="create_id"
        )
        
        creator = st.text_input("Votre pseudo", placeholder="Entrez votre pseudo...", key="creator")
        description = st.text_area(
            "Description du projet", 
            placeholder="Décrivez brièvement votre projet...", 
            height=100,
            key="description"
        )
        
        # Aide pour le format de l'ID
        with st.expander("📝 Format de l'identifiant"):
            st.markdown("""
            L'identifiant doit respecter les règles suivantes :
            - **6 caractères minimum**
            - **Lettres** (sans accents) : A-Z, a-z
            - **Chiffres** : 0-9
            - **Underscore** : _
            - **Exemples valides** : `mon_projet`, `PROJET123`, `test_456`
            - **Exemples invalides** : `mon-projet`, `projet@test`, `échantillon`
            """)
        
        if st.button("Créer le projet", type="primary", key="create_btn"):
            if not new_id:
                st.error("❌ Veuillez saisir un identifiant.")
            elif not creator:
                st.error("❌ Veuillez saisir votre pseudo.")
            elif not description:
                st.error("❌ Veuillez saisir une description.")
            else:
                is_valid, error_msg = is_valid_project_id(new_id)
                if is_valid:
                    if project_exists(new_id):
                        st.error("❌ Cet identifiant est déjà utilisé. Choisissez-en un autre.")
                    else:
                        create_project(new_id, creator, description)
                        st.session_state.project_id = new_id
                        st.session_state.project_data = get_project(new_id)
                        # Sauvegarder dans les query params
                        set_project_to_query_params(new_id)
                        st.success(f"✅ Projet **{new_id}** créé avec succès !")
                        st.rerun()
                else:
                    st.error(f"❌ {error_msg}")

# Page principale de l'application
else:
    # En-tête avec le bouton "Quitter le projet"
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.title(f"Projet : {st.session_state.project_id}")
    
    with col2:
        if st.button("🚪 Quitter le projet"):
            st.session_state.project_id = None
            st.session_state.project_data = None
            st.session_state.just_left_project = True
            # Supprimer des query params
            set_project_to_query_params(None)
            st.rerun()
    
    st.markdown("---")
    
    # Affichage des informations du projet
    project_data = st.session_state.project_data
    if project_data:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Créateur", project_data[3])
            st.metric("Date de création", datetime.datetime.fromisoformat(project_data[1]).strftime("%d/%m/%Y %H:%M"))
        
        with col2:
            st.metric("Dernière modification", datetime.datetime.fromisoformat(project_data[2]).strftime("%d/%m/%Y %H:%M"))
        
        with col3:
            st.metric("Statut", "Actif")
        
    # Section principale de l'application
    st.subheader("Description du projet")
    st.write(project_data[4] if project_data else "Aucune description")
    
    st.markdown("---")
        
    # Vérifier si on est en mode édition de paroles
    if 'current_morceau_id' in st.session_state:
        edition_paroles_tableur(
            st.session_state.current_morceau_id,
            st.session_state.get('current_morceau_titre', '')
        )
    else:
        # Sinon afficher la gestion des morceaux
        gestion_morceaux(st.session_state.project_id)

# Pied de page
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>Application de gestion de projets</div>", 
    unsafe_allow_html=True
)