import streamlit as st
import tempfile
import subprocess
import os

st.title("Mini compilateur LaTeX")

st.write("Entrez du code LaTeX brut :")

default_tex = r"""
\documentclass{article}
\begin{document}
Hello \LaTeX !

Voici une formule :

\[
E = mc^2
\]

\end{document}
"""

latex_code = st.text_area("Code LaTeX :", default_tex, height=300)

if st.button("Compiler en PDF"):
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

        # Vérifier qu'un PDF a été généré
        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                st.success("Compilation réussie ✔️")
                st.download_button("Télécharger le PDF", f, file_name="output.pdf")
        else:
            st.error("Erreur de compilation ❌")
            st.text(result.stdout.decode())
            st.text(result.stderr.decode())
