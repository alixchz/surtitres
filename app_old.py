"""
Streamlit multipage-style single-file app for managing multiple projects (each with a unique code)
that hold editable spreadsheets (textes.ods and titres.ods), persist them on disk, generate .tex files
and compile a PDF with pdflatex.

Files and requirements
----------------------
Save this as `app.py`.

Requirements (put in requirements.txt):
streamlit
pandas
numpy
odfpy
python-dateutil

You also need a LaTeX distribution (pdflatex) installed on the host for compilation.

How to run
----------
1. Install requirements: `pip install -r requirements.txt`
2. Launch Streamlit: `streamlit run app.py`

Notes
-----
- The app stores projects under a folder `projects/` located next to app.py.
- Each project folder contains: metadata.json, textes.ods, titres.ods, pdf/ and generated .tex files.
- If pdflatex is absent, the app will still generate .tex files; compiling will fail with a helpful message.

"""

import streamlit as st
import pandas as pd
import numpy as np
import os
import json
from pathlib import Path
import datetime
import random
import string
import tempfile
import shutil
import subprocess
import zipfile

# ------------------------- Configuration -------------------------
BASE_DIR = Path("projects")
BASE_DIR.mkdir(exist_ok=True)

DEFAULT_TEXTES_COLUMNS = ["Français", "Italien"]
DEFAULT_TITRES_COLUMNS = ["Opéra", "Air", "Compositeur", "Année"]

# LaTeX templates (simple, based on user's template)
TEMPLATE_FRAME = r"""
\begin{frame}{}
    \centering
    \vspace{-2.5cm}
    \textit{\color{lightgray}
        italien_1  \\
        italien_2
    }
    \vskip0.2cm
    francais_1 \\
    francais_2
\end{frame}
"""

TEMPLATE_TITLE = r"""
\begin{frame}{}
    \centering
    \vspace{-2.5cm}
    \textit{\color{black}
        .  \\
        .
    }
    \vskip0.2cm
    \textbf{\textit{opera}} -- compositeur (year)\\
    air
\end{frame}
"""

ARTIFICIAL_SPACE = "{\\color{black}.}"

# ------------------------- Helpers -------------------------

def generate_code(prefix_choices=None):
    if prefix_choices is None:
        prefix_choices = ["lyra", "orfeo", "opera", "belcanto", "libretto", "aria", "cantus", "vocalis", "notturno"]
    prefix = random.choice(prefix_choices)
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{prefix}-{suffix}"


def cleartitle(entry: str) -> str:
    if not isinstance(entry, str):
        entry = str(entry)
    return ''.join(e for e in entry if e.isalnum())


def now_iso():
    return datetime.datetime.utcnow().isoformat()


# Project metadata read/write
def project_dir_from_code(code: str) -> Path:
    safe = ''.join(c for c in code if c.isalnum() or c in ('-', '_'))
    return BASE_DIR / safe


def load_metadata(proj_dir: Path) -> dict:
    meta_file = proj_dir / 'metadata.json'
    if meta_file.exists():
        return json.loads(meta_file.read_text(encoding='utf-8'))
    return {}


def save_metadata(proj_dir: Path, meta: dict):
    meta_file = proj_dir / 'metadata.json'
    meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')


# ODS read/write helpers
def read_ods(path: Path, fallback_empty_df=None):
    try:
        return pd.read_excel(path, engine='odf')
    except Exception as e:
        # fallback to csv if necessary
        st.warning(f"Impossible de lire {path.name} via odf engine: {e}")
        if fallback_empty_df is not None:
            return fallback_empty_df
        return pd.DataFrame()


def write_ods(df: pd.DataFrame, path: Path):
    try:
        df.to_excel(path, engine='odf', index=False)
        return True, None
    except Exception as e:
        return False, str(e)


# Clean functions from user's script

def clean(entry):
    if isinstance(entry, float) or isinstance(entry, np.floating):
        return ARTIFICIAL_SPACE
    if pd.isna(entry):
        return ARTIFICIAL_SPACE
    return str(entry)


# LaTeX generation

def generate_tex_from_textes(df: pd.DataFrame, dest_dir: Path, prefix='frames'):
    dest_dir.mkdir(parents=True, exist_ok=True)
    tex_filename = dest_dir / f"{prefix}.tex"
    # remove existing
    if tex_filename.exists():
        tex_filename.unlink()

    # produce frames by pairs
    rows = df.copy().reset_index(drop=True)
    i = 0
    with tex_filename.open('a', encoding='utf-8') as f:
        while i < len(rows):
            fr_1 = clean(rows.iloc[i].get('Français', ARTIFICIAL_SPACE))
            it_1 = clean(rows.iloc[i].get('Italien', ARTIFICIAL_SPACE))
            if i + 1 < len(rows):
                fr_2 = clean(rows.iloc[i + 1].get('Français', ARTIFICIAL_SPACE))
                it_2 = clean(rows.iloc[i + 1].get('Italien', ARTIFICIAL_SPACE))
            else:
                fr_2 = ARTIFICIAL_SPACE
                it_2 = ARTIFICIAL_SPACE
            content = TEMPLATE_FRAME.replace('italien_1', it_1).replace('italien_2', it_2).replace('francais_1', fr_1).replace('francais_2', fr_2)
            f.write(content + "\n")
            i += 2
    return tex_filename


def generate_title_tex_from_titres(df: pd.DataFrame, dest_dir: Path):
    dest_dir.mkdir(parents=True, exist_ok=True)
    generated_files = []
    for i in range(len(df)):
        opera = str(df.iloc[i].get('Opéra', ''))
        aria = str(df.iloc[i].get('Air', ''))
        compositeur = str(df.iloc[i].get('Compositeur', ''))
        year = str(df.iloc[i].get('Année', ''))
        name = cleartitle(aria) or f"title_{i}"
        tex_filename = dest_dir / f"title_{name}.tex"
        if tex_filename.exists():
            tex_filename.unlink()
        content = TEMPLATE_TITLE.replace('opera', opera).replace('air', aria).replace('compositeur', compositeur).replace('year', year)
        tex_filename.write_text(content, encoding='utf-8')
        generated_files.append(tex_filename)
    return generated_files


# pdflatex compile

def compile_pdf(tex_files: list, workdir: Path, output_name: str = 'sortie.pdf'):
    """Run pdflatex; tex_files is a list of tex filenames to include in the compilation.
    We'll create a master file that \input{} the other files, then run pdflatex twice.
    Returns (success_bool, log_text)
    """
    master = workdir / 'master.tex'
    # A minimal LaTeX preamble
    preamble = r"""
\documentclass{beamer}
\usepackage[utf8]{inputenc}
\usepackage{xcolor}
\begin{document}
"""
    ending = r"""
\end{document}
"""
    body = ''
    for t in tex_files:
        body += f"\\input{{{t.name}}}\n"

    master.write_text(preamble + body + ending, encoding='utf-8')

    # run pdflatex twice
    cmd = ['pdflatex', '-interaction=nonstopmode', master.name]
    logs = ''
    try:
        for _ in range(2):
            proc = subprocess.run(cmd, cwd=workdir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
            logs += proc.stdout.decode('utf-8', errors='ignore') + '\n' + proc.stderr.decode('utf-8', errors='ignore') + '\n'
            if proc.returncode != 0:
                return False, logs
        # move produced pdf to output_name
        produced = workdir / 'master.pdf'
        if produced.exists():
            outpath = workdir / 'pdf'
            outpath.mkdir(exist_ok=True)
            final = outpath / output_name
            shutil.move(str(produced), final)
            return True, logs
        return False, logs + '\nNo PDF produced.'
    except FileNotFoundError as e:
        return False, f"pdflatex not found: {e}"
    except Exception as e:
        return False, f"Compilation error: {e}\nLogs:\n{logs}"


# ------------------------- Streamlit UI -------------------------

st.set_page_config(page_title="Aria Project Manager", layout='wide')

# Sidebar - project selector/create
st.sidebar.header("Projets")
mode = st.sidebar.radio("Mode", ["Ouvrir/Créer projet", "Lister projets", "Importer projet (zip)"])

if mode == 'Ouvrir/Créer projet':
    st.sidebar.subheader('Créer ou charger')
    project_code_input = st.sidebar.text_input('Code du projet (mot-clé unique)', key='proj_code')
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.sidebar.button('Générer code'):
            st.session_state['proj_code'] = generate_code()
    with col2:
        if st.sidebar.button('Créer / Charger'):
            if not st.session_state.get('proj_code'):
                st.sidebar.error('Choisis ou génère un code de projet')
            else:
                # create folder if missing
                pd = project_dir_from_code(st.session_state['proj_code'])
                pd.mkdir(parents=True, exist_ok=True)
                meta = load_metadata(pd)
                if not meta:
                    meta = {'project_id': st.session_state['proj_code'], 'created_at': now_iso(), 'last_modified': now_iso(), 'name': ''}
                    save_metadata(pd, meta)
                st.sidebar.success(f"Projet chargé: {st.session_state['proj_code']}")

elif mode == 'Lister projets':
    st.sidebar.subheader('Projets existants')
    projects = sorted([p.name for p in BASE_DIR.iterdir() if p.is_dir()])
    selected = st.sidebar.selectbox('Sélectionner un projet', [''] + projects)
    if selected:
        st.session_state['proj_code'] = selected
        st.sidebar.success(f"Projet {selected} chargé")

elif mode == 'Importer projet (zip)':
    st.sidebar.subheader('Importer')
    up = st.sidebar.file_uploader('Charger un zip de projet', type=['zip'])
    if up is not None:
        try:
            with tempfile.TemporaryDirectory() as td:
                zpath = Path(td) / 'upload.zip'
                zpath.write_bytes(up.getvalue())
                with zipfile.ZipFile(zpath, 'r') as z:
                    # expect a top-level folder name
                    names = z.namelist()
                    top = names[0].split('/')[0]
                    dest = BASE_DIR / top
                    if dest.exists():
                        st.sidebar.error('Un projet du même nom existe déjà')
                    else:
                        z.extractall(BASE_DIR)
                        st.sidebar.success(f'Projet importé sous {top}')
        except Exception as e:
            st.sidebar.error(f'Erreur import: {e}')

# If no project selected/created, show landing/help
if 'proj_code' not in st.session_state or not st.session_state['proj_code']:
    st.title('Aria Project Manager')
    st.info("Crée ou charge un projet via la barre latérale. \n " \
    "Tu peux générer un code, saisir un mot-clé, ou sélectionner un projet existant.")
    st.write('Fonctionnalités :')
    st.write('- Edition des textes (tableau éditable)')
    st.write('- Edition des titres (tableau éditable)')
    st.write('- Génération de LaTeX et compilation en PDF')
    st.write('- Export / import de projet (zip)')
    st.stop()

# From here, a project is loaded
project_code = st.session_state['proj_code']
proj_dir = project_dir_from_code(project_code)
proj_dir.mkdir(exist_ok=True)
meta = load_metadata(proj_dir)
meta.setdefault('project_id', project_code)
meta.setdefault('created_at', now_iso())
meta['last_modified'] = now_iso()
save_metadata(proj_dir, meta)

# Top nav
page = st.sidebar.selectbox('Page', ['Dashboard', 'Éditer Textes', 'Éditer Titres', 'Générer PDF', 'Exporter / Supprimer'])

st.header(f"Projet: {project_code}")
if meta.get('name'):
    st.subheader(meta.get('name'))

# ------------------ Dashboard ------------------
if page == 'Dashboard':
    st.markdown('**Infos projet :**')
    st.json(meta)
    # show previews
    textes_path = proj_dir / 'textes.ods'
    titres_path = proj_dir / 'titres.ods'
    col1, col2 = st.columns(2)
    with col1:
        st.write('Textes (preview)')
        if textes_path.exists():
            try:
                df = read_ods(textes_path, fallback_empty_df=pd.DataFrame(columns=DEFAULT_TEXTES_COLUMNS))
                st.dataframe(df.head(20))
            except Exception as e:
                st.error(e)
        else:
            st.info('Pas encore de textes')
    with col2:
        st.write('Titres (preview)')
        if titres_path.exists():
            df = read_ods(titres_path, fallback_empty_df=pd.DataFrame(columns=DEFAULT_TITRES_COLUMNS))
            st.dataframe(df.head(20))
        else:
            st.info('Pas encore de titres')

# ------------------ Edit Textes ------------------
elif page == 'Éditer Textes':
    st.subheader('Tableau éditable : Textes (Français / Italien)')
    textes_path = proj_dir / 'textes.ods'
    if textes_path.exists():
        df = read_ods(textes_path, fallback_empty_df=pd.DataFrame(columns=DEFAULT_TEXTES_COLUMNS))
    else:
        df = pd.DataFrame({c: [""] for c in DEFAULT_TEXTES_COLUMNS})

    edited = st.data_editor(df, num_rows='dynamic', key='textes_editor')

    cols = st.columns(3)
    if cols[0].button('Sauvegarder Textes'):
        ok, err = write_ods(edited, textes_path)
        if ok:
            meta['last_modified'] = now_iso()
            save_metadata(proj_dir, meta)
            st.success('Textes sauvegardés')
        else:
            st.error(f'Erreur sauvegarde: {err}')
    if cols[1].button('Ajouter ligne vide'):
        edited = pd.concat([edited, pd.DataFrame({c: [''] for c in edited.columns})], ignore_index=True)
        st.experimental_rerun()
    if cols[2].button('Supprimer lignes vides'):
        cleaned = edited.dropna(how='all')
        write_ods(cleaned, textes_path)
        st.success('Lignes vides supprimées')

# ------------------ Edit Titres ------------------
elif page == 'Éditer Titres':
    st.subheader('Tableau éditable : Titres')
    titres_path = proj_dir / 'titres.ods'
    if titres_path.exists():
        df = read_ods(titres_path, fallback_empty_df=pd.DataFrame(columns=DEFAULT_TITRES_COLUMNS))
    else:
        df = pd.DataFrame({c: [''] for c in DEFAULT_TITRES_COLUMNS})

    edited = st.data_editor(df, num_rows='dynamic', key='titres_editor')

    cols = st.columns(3)
    if cols[0].button('Sauvegarder Titres'):
        ok, err = write_ods(edited, titres_path)
        if ok:
            meta['last_modified'] = now_iso()
            save_metadata(proj_dir, meta)
            st.success('Titres sauvegardés')
        else:
            st.error(f'Erreur sauvegarde: {err}')
    if cols[1].button('Ajouter ligne vide'):
        edited = pd.concat([edited, pd.DataFrame({c: [''] for c in edited.columns})], ignore_index=True)
        st.experimental_rerun()
    if cols[2].button('Supprimer lignes vides'):
        cleaned = edited.dropna(how='all')
        write_ods(cleaned, titres_path)
        st.success('Lignes vides supprimées')

# ------------------ Generate PDF ------------------
elif page == 'Générer PDF':
    st.subheader('Génération LaTeX et compilation PDF')
    textes_path = proj_dir / 'textes.ods'
    titres_path = proj_dir / 'titres.ods'
    if not textes_path.exists() and not titres_path.exists():
        st.warning("Aucun fichiers textes ni titres trouvés. Sauvegarde d'abord les tableaux.")
        st.stop()

    # Load dataframes
    df_textes = read_ods(textes_path, fallback_empty_df=pd.DataFrame(columns=DEFAULT_TEXTES_COLUMNS)) if textes_path.exists() else pd.DataFrame(columns=DEFAULT_TEXTES_COLUMNS)
    df_titres = read_ods(titres_path, fallback_empty_df=pd.DataFrame(columns=DEFAULT_TITRES_COLUMNS)) if titres_path.exists() else pd.DataFrame(columns=DEFAULT_TITRES_COLUMNS)

    st.write('Aperçu des textes :')
    st.dataframe(df_textes.head(30))
    st.write('Aperçu des titres :')
    st.dataframe(df_titres.head(30))

    compile_opt = st.checkbox('Compiler le PDF (nécessite pdflatex)', value=True)
    tex_only = st.checkbox('Générer seulement les fichiers .tex (ne pas compiler)', value=False)

    if st.button('Générer .tex et/ou PDF'):
        generated_dir = proj_dir / 'generated_tex'
        if generated_dir.exists():
            shutil.rmtree(generated_dir)
        generated_dir.mkdir(parents=True)

        frames_tex = generate_tex_from_textes(df_textes, generated_dir, prefix='frames')
        title_tex_files = generate_title_tex_from_titres(df_titres, generated_dir)

        st.success(f'.tex générés dans {generated_dir}')
        if tex_only:
            st.info('Mode .tex seulement — compilation non lancée')
        elif compile_opt:
            st.info('Compilation en cours...')
            tex_file_list = [frames_tex] + title_tex_files
            ok, logs = compile_pdf(tex_file_list, generated_dir, output_name=f'{project_code}_sortie.pdf')
            if ok:
                final_pdf = generated_dir / 'pdf' / f'{project_code}_sortie.pdf'
                dest_pdf_dir = proj_dir / 'pdf'
                dest_pdf_dir.mkdir(exist_ok=True)
                shutil.copy(final_pdf, dest_pdf_dir / final_pdf.name)
                st.success('PDF compilé avec succès')
                with open(dest_pdf_dir / final_pdf.name, 'rb') as f:
                    st.download_button('Télécharger le PDF', f, file_name=final_pdf.name)
            else:
                st.error('Compilation échouée')
                st.text_area('Logs de compilation', value=logs, height=300)
        else:
            st.info('Génération .tex faite — compilation non lancée')
            st.write('Fichiers :')
            for p in [frames_tex] + title_tex_files:
                st.write(p.name)

# ------------------ Export / Delete ------------------
elif page == 'Exporter / Supprimer':
    st.subheader('Exporter ou supprimer le projet')
    col1, col2 = st.columns(2)
    with col1:
        if st.button('Exporter projet en zip'):
            zipname = BASE_DIR / f"{project_code}.zip"
            with zipfile.ZipFile(zipname, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(proj_dir):
                    for f in files:
                        filepath = Path(root) / f
                        arcname = filepath.relative_to(BASE_DIR)
                        zf.write(filepath, arcname)
            with open(zipname, 'rb') as fh:
                st.download_button('Télécharger le zip', fh, file_name=zipname.name)
    with col2:
        st.write('Supprimer le projet définitivement')
        confirm = st.text_input('Tape SUPPRIMER pour confirmer', '')
        if st.button('Supprimer projet'):
            if confirm == 'SUPPRIMER':
                shutil.rmtree(proj_dir)
                st.success('Projet supprimé')
                st.stop()
            else:
                st.error('Confirmation incorrecte')

# Footer: metadata edit
st.sidebar.markdown('---')
new_name = st.sidebar.text_input('Nom du projet', value=meta.get('name', ''), key='meta_name')
if st.sidebar.button('Mettre à jour métadonnées'):
    meta['name'] = new_name
    meta['last_modified'] = now_iso()
    save_metadata(proj_dir, meta)
    st.sidebar.success('Metadata mise à jour')


# End
st.sidebar.write('Projects folder: ' + str(BASE_DIR.resolve()))


# EOF
