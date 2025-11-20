import pandas as pd
import os 
import numpy 

template = """
\\begin{frame}{}
    \centering
    \\vspace{-2.5cm}
    \\textit{\color{lightgray}
        italien_1  \\\\
        italien_2
    }
    \\vskip0.2cm
    francais_1 \\\\
    francais_2
\end{frame}"""
artificial_space = "{\\color{black}.}"

def clean(entry):
    if type(entry) in (float, numpy.float64):
        return artificial_space
    return entry

def cleartitle(entry):
    # garder uniquement les lettres sans accents sans espaces
    return ''.join(e for e in entry if e.isalnum())

for aria in ['princesse', 'viaresti','aprite', 'lacidaremlamano', 'lacidaremlamano_norecit', 'notteegiornofaticar', 'maquaimaisoffre', 'prenderoquelbrunettino', 'ciboulette', 'jaipasenvie']:
    df = pd.read_excel(f'textes_source/{aria}.ods', engine='odf')
    df
    tex_filename = f"frames_{aria}.tex"
    if os.path.exists(tex_filename):
        os.remove(tex_filename)

    while len(df) !=0:
        with open(tex_filename, "a") as f:
            fr_1 = clean(df.iloc[0]["Français"])
            it_1 = clean(df.iloc[0]["Italien"])
            if len(df) == 1:
                fr_2 = artificial_space
                it_2 = artificial_space
                df = []
            else:
                fr_2 = clean(df.iloc[1]["Français"])
                it_2 = clean(df.iloc[1]["Italien"])
                if len(df) >= 2:
                    df = df[2:]
            content = template.replace("italien_1", it_1).replace("italien_2", it_2).replace("francais_1", fr_1).replace("francais_2", fr_2)
            f.write(content)


template_titre = """
\\begin{frame}{}
    \centering
    \\vspace{-2.5cm}
    \\textit{\color{black}
        .  \\\\
        .
    }
    \\vskip0.2cm
    \\textbf{\\textit{opera}} -- compositeur (year)\\\\
    air
\end{frame}"""

titres = pd.read_excel('titres.ods', engine='odf')
for i in range(len(titres)):
    opera = titres.iloc[i]['Opéra']
    aria = titres.iloc[i]['Air']
    compositeur = titres.iloc[i]['Compositeur']
    year = titres.iloc[i]['Année']
    tex_filename = f"title_frames/title_{cleartitle(aria)}.tex"
    if os.path.exists(tex_filename):
        os.remove(tex_filename)
    with open(tex_filename, "a") as f:
        content = template_titre.replace("opera", opera).replace("air", aria).replace("compositeur", compositeur).replace("year", str(year))
        f.write(content)
