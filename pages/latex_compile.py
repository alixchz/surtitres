import tempfile
import subprocess
import base64
import os
import streamlit as st

st.title("Mini compilateur LaTeX avec aperçu PDF")

# --- Layout : deux colonnes ---
col_left, col_right = st.columns([1, 1])

with col_left:
    default_tex = r"""
\documentclass[9pt,aspectratio=169]{beamer}

% Packages utiles
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[french]{babel}
\usepackage{lmodern}
\usepackage{hyperref}
\usepackage{graphicx}
\usepackage{minted} % si vous voulez du code (nécessite -shell-escape)

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
Blabla

\end{document}
"""
latex_code = st.text_area("Code LaTeX :", default_tex, height=400)
compile_btn = st.button("Compiler en PDF")

with col_right:
    st.subheader("Aperçu PDF")

# Bouton de compilation
if compile_btn:
    with tempfile.TemporaryDirectory() as tmpdir:

        tex_path = os.path.join(tmpdir, "doc.tex")
        pdf_path = os.path.join(tmpdir, "doc.pdf")

        # Écrire le .tex
        with open(tex_path, "w") as f:
            f.write(latex_code)

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
                f'<iframe src="data:application/pdf;base64,{base64_pdf}" '
                f'width="100%" height="600px" type="application/pdf"></iframe>'
            )

            with col_right:
                st.markdown(pdf_display, unsafe_allow_html=True)

            # --- Bouton de téléchargement ---
            with col_right:
                st.download_button("Télécharger le PDF", pdf_bytes, file_name="output.pdf")

        else:
            st.error("Erreur de compilation ❌")
            st.text(result.stdout.decode())
            st.text(result.stderr.decode())
