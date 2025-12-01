import pandas as pd
import os 
import numpy 
import sqlite3
import streamlit as st
import tempfile
import subprocess
import base64

template = """
\\begin{frame}{}
    \\centering
    \\vspace{-2.5cm}
    \\textit{\color{lightgray}
        original_1  \\\\
        original_2
    }
    \\vskip0.2cm
    francais_1 \\\\
    francais_2
\end{frame}"""

artificial_space = "{\\color{black}.}"

template_titre = """
\\begin{frame}{}
    \\centering
    \\vspace{-2.5cm}
    \\textit{\color{black}
        .  \\\\
        .
    }
    \\vskip0.2cm
    opera compositeur year\\\\
    « air »
\end{frame}"""

def clean(entry):
    if type(entry) in (float, numpy.float64):
        return artificial_space
    return entry.replace('[', '').replace(']', '')

def cleartitle(entry):
    # garder uniquement les lettres sans accents sans espaces
    return ''.join(e for e in entry if e.isalnum())

def get_morceau(morceau_id):
    conn = sqlite3.connect('projects.db')
    c = conn.cursor()
    c.execute('''
        SELECT id, ordre, air, compositeur, annee, extrait_de 
        FROM morceaux 
        WHERE id = ? 
        ORDER BY ordre
    ''', (morceau_id,))
    result = c.fetchall()
    conn.close()
    return result[0]

def generate_frame_title(morceau_id):
    morceau = get_morceau(morceau_id)
    air, compositeur, annee, extrait_de = morceau[2], morceau[3], morceau[4], morceau[5]

    title_frame = template_titre.replace("air", air).replace("compositeur", compositeur)
    title_frame = title_frame.replace("opera", f"\\textbf{{\\textit{{extrait_de}}}} -- ".replace("extrait_de", extrait_de)) if len(extrait_de) > 0 else title_frame.replace("opera", "")
    title_frame = title_frame.replace("year", f"({str(annee)})") if len(annee) >0 else title_frame.replace("year", "")
    return title_frame

def generate_text(paroles_df):  
    tex_slides = ""  
    df = paroles_df
    while len(df) !=0:
        fr_1 = clean(df.iloc[0]["Traduction"])
        it_1 = clean(df.iloc[0]["Original"])
        if len(df) == 1:
            fr_2 = artificial_space
            it_2 = artificial_space
            df = []
        else:
            fr_2 = clean(df.iloc[1]["Traduction"])
            it_2 = clean(df.iloc[1]["Original"])
            if len(df) >= 2:
                df = df[2:]
        content = template.replace("original_1", it_1).replace("original_2", it_2).replace("francais_1", fr_1).replace("francais_2", fr_2)
        tex_slides += content + "\n"
    return tex_slides

default_tex = r"""
    \documentclass[9pt,aspectratio=169]{beamer}

    % Packages utiles
    \usepackage[utf8]{inputenc}
    \usepackage[T1]{fontenc}
    \usepackage[french]{babel}
    \usepackage{lmodern}
    \usepackage{hyperref}
    \usepackage{graphicx}

    % Couleurs : fond noir, texte blanc
    \setbeamercolor{background canvas}{bg=black}
    \setbeamercolor{normal text}{fg=white}
    \setbeamercolor{frametitle}{fg=white,bg=black}
    \setbeamercolor{title}{fg=white,bg=black}
    \setbeamercolor{author}{fg=white}
    \setbeamercolor{date}{fg=white}
    \setbeamercolor{section in toc}{fg=white}
    \setbeamercolor{subsection in toc}{fg=white}
    \setbeamercolor{item}{fg=white}
    \setbeamercolor{enumerate item}{fg=white}
    \setbeamercolor{block title}{fg=black,bg=white!10} % titres de block légèrement clairs
    \setbeamercolor{block body}{fg=white,bg=black}
    \setbeamercolor{caption name}{fg=white}
    % Create a light gray color
    \usepackage{xcolor}
    \definecolor{lightgray}{rgb}{0.7, 0.7, 0.7}

    \setbeamersize{text margin left=1.5cm, text margin right=1.5cm}

    % Remove navigation symbols (optionnel)
    \setbeamertemplate{navigation symbols}{}

    \begin{document}
    %CONTENT

    \end{document}
    """

def make_latex(frames):
    content = default_tex.replace("%CONTENT", frames)

    with tempfile.TemporaryDirectory() as tmpdir:

        tex_path = os.path.join(tmpdir, "doc.tex")
        pdf_path = os.path.join(tmpdir, "doc.pdf")

        # Écrire le .tex
        with open(tex_path, "w") as f:
            f.write(content)

        # Compiler
        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", tex_path],
            cwd=tmpdir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        if os.path.exists(pdf_path):

            # Lire le PDF pour affichage
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()

            # --- Affichage PDF dans le navigateur ---
            base64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
            pdf_display = (
                f'<iframe src="data:application/pdf;base64,{base64_pdf}#zoom=page-width" '
                f'width="80%" height="600px" type="application/pdf"></iframe>'
            )

            st.markdown(pdf_display, unsafe_allow_html=True)
            col_pdf, col_tex = st.columns(2)
            # --- Bouton de téléchargement ---
            with col_pdf:
                st.download_button("Télécharger le PDF", pdf_bytes, file_name="surtitres.pdf")
            with col_tex:
                st.download_button("Télécharger le code LaTeX", content, file_name="surtitres.tex")

        else:
            st.error("Erreur de compilation ❌")
            def safe_decode(data):
                try:
                    return data.decode("utf-8")
                except UnicodeDecodeError:
                    return data.decode("latin-1")

            st.text(safe_decode(result.stdout))
            st.text(safe_decode(result.stderr))
            st.download_button("Télécharger le code LaTeX", content, file_name="surtitres.tex")