import streamlit as st
import pandas as pd
import random
import os

# --- Injection de CSS pour personnaliser l'apparence ---
st.markdown(
    """
    <style>
    /* Personnalisation de l'arrière-plan principal */
    .main { background-color: #f7f7f7; }
    
    /* Personnalisation de la sidebar */
    .css-1d391kg {  /* Classe générée par Streamlit - peut varier */
        background: linear-gradient(135deg, #2e7bcf, #2e7bcf);
        color: white;
    }
    
    /* Style du header */
    .header {
        font-family: 'Helvetica Neue', sans-serif;
        font-size: 2.5em;
        font-weight: bold;
        color: #2e7bcf;
        text-align: center;
        margin-bottom: 20px;
    }
    
    /* Style des feedback */
    .feedback-correct { color: green; font-weight: bold; }
    .feedback-incorrect { color: red; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True
)

# --- Chemins des fichiers CSV ---
csv_path = os.path.expanduser("finalV3.csv")
glossaire_csv_path = os.path.expanduser("glossaire.csv")

# --- Fonctions auxiliaires ---
def get_genus(scientific_name):
    if not scientific_name:
        return ""
    return scientific_name.split()[0]

def get_species_name(scientific_name):
    words = scientific_name.split()
    if len(words) >= 2:
        return " ".join(words[:2])
    return scientific_name

# --- Chargement des données ---
@st.cache_data
def load_quiz_data():
    df = pd.read_csv(csv_path, sep=";")
    # Conversion de la colonne "Images" en liste si nécessaire
    df["Images"] = df["Images"].apply(lambda x: x.split(";") if isinstance(x, str) else x)
    return df

@st.cache_data
def load_glossaire_data():
    df = pd.read_csv(glossaire_csv_path)
    return df

quiz_data = load_quiz_data()
# Calcul de la colonne Genus pour faciliter la sélection
quiz_data["Genus"] = quiz_data["Nom_scientifique"].apply(get_genus)
glossaire_data = load_glossaire_data()

# --- Initialisation de l'état de session ---
if "question" not in st.session_state:
    st.session_state.question = None
if "current_img_index" not in st.session_state:
    st.session_state.current_img_index = 0
if "score" not in st.session_state:
    st.session_state.score = 0
if "total" not in st.session_state:
    st.session_state.total = 0
if "feedback" not in st.session_state:
    st.session_state.feedback = ""

# --- En-tête personnalisé ---
st.markdown("<div class='header'>Quiz Botanique</div>", unsafe_allow_html=True)

# --- Barre latérale ---
st.sidebar.title("Options")
mode = st.sidebar.radio(
    "Mode de jeu :", 
    [
        "Facile", 
        "Difficile", 
        "Extrêmement difficile", 
        "Entrainement facile", 
        "Entrainement difficile",
        "Glossaire : définition → terme",
        "Glossaire : terme → définition"
    ],
    index=0
)

# Pour les modes d'entraînement, on permet de choisir le critère de travail
training_type = None  # "Famille" ou "Genre"
training_value = None  # Valeur sélectionnée pour le critère
if mode in ["Entrainement facile", "Entrainement difficile"]:
    training_type = st.sidebar.radio("S'entraîner sur :", ["Famille", "Genre"])
    if training_type == "Famille":
        training_value = st.sidebar.selectbox(
            "Choisissez la famille :", 
            sorted(quiz_data["Famille"].unique())
        )
    else:  # Entraînement sur Genre
        training_family = st.sidebar.selectbox(
            "Choisissez la famille pour filtrer les genres :", 
            sorted(quiz_data["Famille"].unique())
        )
        # On filtre les genres disponibles dans la famille choisie
        genres_disponibles = sorted(quiz_data[quiz_data["Famille"] == training_family]["Genus"].unique())
        training_value = st.sidebar.selectbox("Choisissez le genre :", genres_disponibles)

# --- Bouton Nouvelle Question ---
if st.sidebar.button("Nouvelle Question"):
    if mode in ["Facile", "Difficile", "Extrêmement difficile", "Entrainement facile", "Entrainement difficile"]:
        # --- Sélection de la donnée d'entraînement selon le critère choisi ---
        if mode in ["Entrainement facile", "Entrainement difficile"]:
            if not training_value:
                st.sidebar.warning("Veuillez choisir une valeur pour l'entraînement.")
            else:
                if training_type == "Famille":
                    training_data = quiz_data[quiz_data["Famille"] == training_value]
                else:  # training_type == "Genre"
                    # Ici, training_family est la famille utilisée pour filtrer, et training_value le genre
                    training_data = quiz_data[(quiz_data["Famille"] == training_family) & (quiz_data["Genus"] == training_value)]
                if training_data.empty:
                    st.sidebar.error(f"Aucune plante trouvée pour {training_type} sélectionné(e).")
                else:
                    quiz_row = training_data.sample(1).iloc[0]
        else:
            quiz_row = quiz_data.sample(1).iloc[0]
            
        quiz_images = quiz_row["Images"]
        st.session_state.current_img_index = 0

        # Préparation du dictionnaire de question (q)
        q = {
            "images": quiz_images,
            "mode": mode,
            "correct_common": quiz_row["Nom_commun"],
            "correct_family": quiz_row["Famille"],
            "taille_plante": quiz_row.get("Taille_Plante", ""),
            "type_vegetatif": quiz_row.get("Type_Végétatif", ""),
            "floraison": quiz_row.get("Floraison", ""),
            "description": quiz_row.get("Description", ""),
            "url": quiz_row.get("URL", "")
        }
        
        # Pour les modes basés sur le nom scientifique complet
        if mode in ["Facile", "Difficile", "Extrêmement difficile"]:
            q["correct_species"] = (
                quiz_row["Nom_scientifique"] 
                if mode not in ["Extrêmement difficile"] 
                else get_species_name(quiz_row["Nom_scientifique"])
            )
            if mode == "Facile":
                available_families = list(set(quiz_data["Famille"].tolist()) - {quiz_row["Famille"]})
                if len(available_families) >= 3:
                    fam_choices = random.sample(available_families, 3) + [quiz_row["Famille"]]
                else:
                    fam_choices = available_families + [quiz_row["Famille"]]
                random.shuffle(fam_choices)
                q["family_choices"] = fam_choices

            if mode in ["Facile", "Difficile"]:
                if mode == "Facile":
                    pool = quiz_data if mode == "Facile" else quiz_data[quiz_data["Famille"] == quiz_row["Famille"]]
                    corr = quiz_row["Nom_scientifique"]
                    available_species = pool[pool["Nom_scientifique"] != corr]["Nom_scientifique"].tolist()
                    if len(available_species) >= 3:
                        choices = random.sample(available_species, 3) + [corr]
                    else:
                        choices = available_species + [corr]
                    random.shuffle(choices)
                    q["species_choices"] = choices
                elif mode == "Difficile":
                    corr = quiz_row["Nom_scientifique"]
                    genus_corr = quiz_row["Genus"]
                    same_genus = quiz_data[quiz_data["Genus"] == genus_corr]
                    same_genus = same_genus[same_genus["Nom_scientifique"] != corr]["Nom_scientifique"].tolist()
                    if len(same_genus) >= 3:
                        other_names = random.sample(same_genus, 3)
                    else:
                        needed = 3 - len(same_genus)
                        available_species = quiz_data[quiz_data["Nom_scientifique"] != corr]["Nom_scientifique"].tolist()
                        other_names = same_genus + random.sample(available_species, min(needed, len(available_species)))
                    choices = [corr] + other_names
                    random.shuffle(choices)
                    q["species_choices"] = choices
        
        # Pour les modes d'entraînement ("Entrainement facile", "Entrainement difficile")
        # Que l'on s'entraîne sur "Famille" ou "Genre", la réponse attendue est le nom scientifique complet (espèce)
        if mode in ["Entrainement facile", "Entrainement difficile"]:
            q["correct_species"] = quiz_row["Nom_scientifique"]
            if mode == "Entrainement facile":
                # Ici, on propose uniquement des espèces parmi les données filtrées (training_data)
                pool = training_data
                corr = quiz_row["Nom_scientifique"]
                available_species = pool[pool["Nom_scientifique"] != corr]["Nom_scientifique"].tolist()
                if len(available_species) >= 3:
                    choices = random.sample(available_species, 3) + [corr]
                else:
                    choices = available_species + [corr]
                random.shuffle(choices)
                q["species_choices"] = choices

        st.session_state.question = q
        st.session_state.feedback = ""
        
    elif mode.startswith("Glossaire"):
        gloss_row = glossaire_data.sample(1).iloc[0]
        q = {"mode": mode}
        if mode == "Glossaire : définition → terme":
            q["definition"] = gloss_row["Definition"]
            q["image"] = gloss_row["Image_URL"]
            q["correct"] = gloss_row["Terme"]
        elif mode == "Glossaire : terme → définition":
            q["terme"] = gloss_row["Terme"]
            q["image"] = gloss_row["Image_URL"]
            q["correct"] = gloss_row["Definition"]
        st.session_state.question = q
        st.session_state.feedback = ""

# --- Bouton Photo suivante ---
if st.sidebar.button("Photo suivante"):
    if st.session_state.question is not None and "images" in st.session_state.question:
        if st.session_state.current_img_index < len(st.session_state.question["images"]) - 1:
            st.session_state.current_img_index += 1
        else:
            st.session_state.current_img_index = 0

# --- Affichage du score avec st.metric et barre de progression ---
st.sidebar.metric("Score", f"{st.session_state.score} / {st.session_state.total}")
progress = 0
if st.session_state.total > 0:
    progress = int(100 * st.session_state.score / st.session_state.total)
st.sidebar.progress(progress)

# --- Partie principale de l'application ---
col1, col2 = st.columns([1, 2])
if st.session_state.question is not None:
    q = st.session_state.question
    
    if "images" in q:
        with col1:
            img_url = q["images"][st.session_state.current_img_index]
            st.image(img_url, width=600)
        with col2:
            st.markdown("#### Répondez à la question")
            # Pour tous les modes basés sur le nom scientifique, on propose la même interface
            if q["mode"] in ["Facile", "Difficile", "Entrainement facile"]:
                species_answer = st.radio("Choisissez le nom scientifique :", q.get("species_choices", []), key="species_radio")
                if q["mode"] == "Facile":
                    family_answer = st.radio("Choisissez la famille :", q.get("family_choices", []), key="family_radio")
                else:
                    family_answer = q["correct_family"]
            elif q["mode"] in ["Extrêmement difficile", "Entrainement difficile"]:
                species_answer = st.text_input("Entrez le genre et l'espèce (ex: Genus species) :", key="typed_species")
                if q["mode"] == "Extrêmement difficile":
                    family_answer = st.text_input("Entrez la famille :", key="typed_family")
                else:
                    family_answer = q["correct_family"]

            if st.button("Valider"):
                mode_q = q["mode"]
                feedback = ""
                
                # Vérification du nom scientifique complet
                if mode_q in ["Facile", "Difficile", "Entrainement facile"]:
                    if species_answer == q["correct_species"]:
                        feedback += "<p class='feedback-correct'>✅ Nom scientifique correct !</p>"
                        species_points = 1
                    else:
                        if get_genus(species_answer).lower() == get_genus(q["correct_species"]).lower():
                            feedback += (
                                f"<p class='feedback-correct'>⚠️ Genre correct, mais espèce incorrecte. La bonne réponse était: {q['correct_species']}</p>"
                            )
                            species_points = 0.5
                        else:
                            feedback += (
                                f"<p class='feedback-incorrect'>❌ Nom scientifique incorrect ! La bonne réponse était: {q['correct_species']}</p>"
                            )
                            species_points = 0
                    if mode_q == "Facile":
                        if family_answer == q["correct_family"]:
                            feedback += "<p class='feedback-correct'>✅ Famille correcte !</p>"
                            family_points = 1
                        else:
                            feedback += (
                                f"<p class='feedback-incorrect'>❌ Famille incorrecte ! La bonne réponse était: {q['correct_family']}</p>"
                            )
                            family_points = 0
                    else:
                        family_points = 0
                    st.session_state.total += 1 if mode_q in ["Entrainement facile"] else 1
                    if mode_q == "Facile":
                        st.session_state.total += 1
                    st.session_state.score += species_points + family_points

                elif mode_q in ["Extrêmement difficile", "Entrainement difficile"]:
                    user_species = species_answer.lower().strip()
                    correct_species = q["correct_species"].lower().strip()
                    if user_species == correct_species:
                        feedback += "<p class='feedback-correct'>✅ Nom scientifique correct !</p>"
                        species_points = 1
                    else:
                        if get_genus(user_species) == get_genus(correct_species):
                            feedback += (
                                f"<p class='feedback-correct'>⚠️ Genre correct, mais espèce incorrecte. La bonne réponse était: {q['correct_species']}</p>"
                            )
                            species_points = 0.5
                        else:
                            feedback += (
                                f"<p class='feedback-incorrect'>❌ Nom scientifique incorrect ! La bonne réponse était: {q['correct_species']}</p>"
                            )
                            species_points = 0
                    if mode_q == "Extrêmement difficile":
                        user_family = family_answer.lower().strip()
                        correct_family = q["correct_family"].lower().strip()
                        if user_family == correct_family:
                            feedback += "<p class='feedback-correct'>✅ Famille correcte !</p>"
                            family_points = 1
                        else:
                            feedback += (
                                f"<p class='feedback-incorrect'>❌ Famille incorrecte ! La bonne réponse était: {q['correct_family']}</p>"
                            )
                            family_points = 0
                    else:
                        family_points = 0
                    if mode_q == "Extrêmement difficile":
                        st.session_state.total += 2
                    else:
                        st.session_state.total += 1
                    st.session_state.score += species_points + family_points

                feedback += f"<p>Nom commun : {q['correct_common']}</p>"
                feedback += f"<p>Taille : {q['taille_plante']}</p>"
                feedback += f"<p>Type végétatif : {q['type_vegetatif']}</p>"
                feedback += f"<p>Floraison : {q['floraison']}</p>"
                feedback += f"<p>Description : {q['description']}</p>"
                if q['url']:
                    feedback += f"<p>Plus d’infos : <a href='{q['url']}' target='_blank'>{q['url']}</a></p>"

                st.session_state.feedback = feedback
                st.markdown("### Feedback")
                st.markdown(st.session_state.feedback, unsafe_allow_html=True)
    
    elif q.get("mode", "").startswith("Glossaire"):
        if q["mode"] == "Glossaire : définition → terme":
            st.markdown("### Définition")
            st.write(q["definition"])
            if pd.notna(q["image"]) and q["image"] != "":
                st.image(q["image"], width=600)
            user_answer = st.text_input("Quel est le terme ?", key="glossaire_answer")
        elif q["mode"] == "Glossaire : terme → définition":
            st.markdown("### Terme")
            st.write(q["terme"])
            if pd.notna(q["image"]) and q["image"] != "":
                st.image(q["image"], width=600)
            user_answer = st.text_input("Quelle est la définition ?", key="glossaire_answer")
        
        if st.button("Valider"):
            if user_answer.lower().strip() == q["correct"].lower().strip():
                st.session_state.feedback = "<p class='feedback-correct'>✅ Correct !</p>"
            else:
                st.session_state.feedback = f"<p class='feedback-incorrect'>❌ Incorrect, la bonne réponse était : {q['correct']}</p>"
            st.markdown("### Feedback")
            st.markdown(st.session_state.feedback, unsafe_allow_html=True)

# --- Pied de page / crédits ---
st.markdown("---")
st.markdown(
    "<div style='font-size:10px; text-align:center; color:gray;'>"
    "Crédits : SOUYRIS Thomas / Photos Plantes : Flore Alpes / "
    "Glossaire : Université catholique de Louvain</div>", 
    unsafe_allow_html=True
)
