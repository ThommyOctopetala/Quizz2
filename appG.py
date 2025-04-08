import streamlit as st
import pandas as pd
import random
import os
import time

# --- Injection de CSS pour personnaliser l'apparence ---
st.markdown(
    """
    <style>
    /* Personnalisation de l'arrière-plan principal */
    .main { background-color: #f7f7f7; }
    
    /* Personnalisation de la sidebar */
    .css-1d391kg {
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
    """,
    unsafe_allow_html=True
)

# --- Chemins des fichiers CSV ---
csv_path = os.path.expanduser("finalV3.csv")
glossaire_csv_path = os.path.expanduser("glossaire.csv")

# --- Fonctions auxiliaires ---
def get_genus(scientific_name):
    """Extrait le genre du nom scientifique."""
    if not scientific_name:
        return ""
    return scientific_name.split()[0]

def get_species_name(scientific_name):
    """
    Extrait le nom de l'espèce au complet ou réduit. 
    Ici on renvoie tout le nom "Genus species", 
    mais vous pourriez choisir de tronquer si besoin.
    """
    return scientific_name.strip()

# --- Chargement des données ---
@st.cache_data
def load_quiz_data():
    df = pd.read_csv(csv_path, sep=";")
    # Conversion de la colonne "Images" en liste si nécessaire
    df["Images"] = df["Images"].apply(lambda x: x.split(";") if isinstance(x, str) else x)
    df["Genus"] = df["Nom_scientifique"].apply(get_genus)
    df["Espece"] = df["Nom_scientifique"].apply(get_species_name)  # stocke le nom complet
    return df

@st.cache_data
def load_glossaire_data():
    df = pd.read_csv(glossaire_csv_path)
    return df

quiz_data = load_quiz_data()
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
if "start_time" not in st.session_state:
    st.session_state.start_time = None  # Pour le mode chronométré
if "time_limit" not in st.session_state:
    st.session_state.time_limit = None  # Pour le mode chronométré

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
        "Glossaire : terme → définition",
        "Correspondance (Famille / Genre / Espèce)",
        "Mode chronométré"
    ],
    index=0
)

# ------------------------------------------------------------
#   Options pour l'entraînement (famille / genre)
# ------------------------------------------------------------
training_type = None
training_value = None

if mode in ["Entrainement facile", "Entrainement difficile"]:
    training_type = st.sidebar.radio(
        "S'entraîner sur :", 
        ["Famille", "Genre"]
    )
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
        genres_disponibles = sorted(quiz_data[quiz_data["Famille"] == training_family]["Genus"].unique())
        training_value = st.sidebar.selectbox("Choisissez le genre :", genres_disponibles)

# ------------------------------------------------------------
#   Options pour le mode "Correspondance (Famille / Genre / Espèce)"
# ------------------------------------------------------------
if mode == "Correspondance (Famille / Genre / Espèce)":
    num_images = st.sidebar.slider("Nombre d'images :", 2, 6, 3)
    type_correspondance = st.sidebar.selectbox(
        "Comparer :",
        [
            "Famille", 
            "Genre", 
            "Espèce",
            "Famille & Genre",
            "Famille & Espèce",
            "Genre & Espèce",
            "Les trois (Famille, Genre, Espèce)"
        ]
    )

# ------------------------------------------------------------
#   Options pour le Mode chronométré
# ------------------------------------------------------------
if mode == "Mode chronométré":
    st.session_state.time_limit = st.sidebar.number_input(
        "Temps limite par question (secondes) :", 
        min_value=10, 
        max_value=120, 
        value=30
    )

# --- Bouton Nouvelle Question ---
if st.sidebar.button("Nouvelle Question"):
    st.session_state.feedback = ""

    # 1. Modes classiques ou entraînement
    if mode in ["Facile", "Difficile", "Extrêmement difficile", "Entrainement facile", "Entrainement difficile"]:
        if mode in ["Entrainement facile", "Entrainement difficile"]:
            if not training_value:
                st.sidebar.warning("Veuillez choisir une valeur pour l'entraînement.")
            else:
                if training_type == "Famille":
                    training_data = quiz_data[quiz_data["Famille"] == training_value]
                else:  # Genre
                    training_data = quiz_data[(quiz_data["Famille"] == training_family) & (quiz_data["Genus"] == training_value)]
                if training_data.empty:
                    st.sidebar.error(f"Aucune plante trouvée pour {training_type}={training_value}.")
                else:
                    quiz_row = training_data.sample(1).iloc[0]
        else:
            # Mode classique (Facile, Difficile, Extrêmement difficile)
            quiz_row = quiz_data.sample(1).iloc[0]

        if "quiz_row" in locals():
            quiz_images = quiz_row["Images"]
            st.session_state.current_img_index = 0

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

            # Pour la plupart des modes, on travaille sur l'espèce
            # sauf si on fait un entraînement sur "Genre" spécifiquement
            if not (mode in ["Entrainement facile", "Entrainement difficile"] and training_type == "Genre"):
                # Nom scientifique complet ou réduit
                if mode != "Extrêmement difficile":
                    q["correct_species"] = quiz_row["Nom_scientifique"]
                else:
                    # En "Extrêmement difficile", on tronque à "Genus species" (si besoin)
                    q["correct_species"] = get_species_name(quiz_row["Nom_scientifique"])

                # Mode Facile : QCM Famille + QCM Espèces
                if mode == "Facile":
                    all_families = list(set(quiz_data["Famille"].tolist()) - {quiz_row["Famille"]})
                    if len(all_families) >= 3:
                        fam_choices = random.sample(all_families, 3) + [quiz_row["Famille"]]
                    else:
                        fam_choices = all_families + [quiz_row["Famille"]]
                    random.shuffle(fam_choices)
                    q["family_choices"] = fam_choices

                    corr = quiz_row["Nom_scientifique"]
                    available_species = quiz_data[quiz_data["Nom_scientifique"] != corr]["Nom_scientifique"].tolist()
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

            # Entrainement sur le Genre
            if mode in ["Entrainement facile", "Entrainement difficile"] and training_type == "Genre":
                q["correct_genus"] = quiz_row["Genus"]
                if mode == "Entrainement facile":
                    pool_genus = quiz_data["Genus"].unique().tolist()
                    pool_genus = [g for g in pool_genus if g != q["correct_genus"]]
                    if len(pool_genus) >= 3:
                        genus_choices = random.sample(pool_genus, 3) + [q["correct_genus"]]
                    else:
                        genus_choices = pool_genus + [q["correct_genus"]]
                    random.shuffle(genus_choices)
                    q["genus_choices"] = genus_choices

            # Enregistrer la question
            st.session_state.question = q

            # Réinitialiser le chrono si c’est le mode chronométré
            if mode == "Mode chronométré":
                st.session_state.start_time = time.time()

    # 2. Mode "Correspondance (Famille / Genre / Espèce)"
    elif mode == "Correspondance (Famille / Genre / Espèce)":
        sampled_rows = quiz_data.sample(num_images)
        images_data = []
        for _, row in sampled_rows.iterrows():
            if isinstance(row["Images"], list) and len(row["Images"]) > 0:
                chosen_img = random.choice(row["Images"])
            else:
                chosen_img = None
            images_data.append({
                "image": chosen_img,
                "family": row["Famille"],
                "genus": row["Genus"],
                "species": row["Espece"],
                "common_name": row["Nom_commun"]
            })
        
        st.session_state.question = {
            "mode": "Correspondance",
            "images_data": images_data,
            "type_correspondance": type_correspondance
        }
        st.session_state.current_img_index = 0

    # 3. Mode chronométré (similaire à un "Facile" QCM)
    elif mode == "Mode chronométré":
        quiz_row = quiz_data.sample(1).iloc[0]
        quiz_images = quiz_row["Images"]
        st.session_state.current_img_index = 0

        q = {
            "images": quiz_images,
            "mode": "Mode chronométré",
            "correct_common": quiz_row["Nom_commun"],
            "correct_family": quiz_row["Famille"],
            "taille_plante": quiz_row.get("Taille_Plante", ""),
            "type_vegetatif": quiz_row.get("Type_Végétatif", ""),
            "floraison": quiz_row.get("Floraison", ""),
            "description": quiz_row.get("Description", ""),
            "url": quiz_row.get("URL", ""),
            "correct_species": quiz_row["Nom_scientifique"],
        }

        # QCM Famille
        all_families = list(set(quiz_data["Famille"].tolist()) - {quiz_row["Famille"]})
        if len(all_families) >= 3:
            fam_choices = random.sample(all_families, 3) + [quiz_row["Famille"]]
        else:
            fam_choices = all_families + [quiz_row["Famille"]]
        random.shuffle(fam_choices)
        q["family_choices"] = fam_choices

        # QCM Espèce
        corr = quiz_row["Nom_scientifique"]
        available_species = quiz_data[quiz_data["Nom_scientifique"] != corr]["Nom_scientifique"].tolist()
        if len(available_species) >= 3:
            choices = random.sample(available_species, 3) + [corr]
        else:
            choices = available_species + [corr]
        random.shuffle(choices)
        q["species_choices"] = choices

        st.session_state.question = q
        st.session_state.start_time = time.time()

# --- Bouton Photo suivante ---
if st.sidebar.button("Photo suivante"):
    if (
        st.session_state.question is not None 
        and "images" in st.session_state.question 
        and isinstance(st.session_state.question["images"], list)
    ):
        if st.session_state.current_img_index < len(st.session_state.question["images"]) - 1:
            st.session_state.current_img_index += 1
        else:
            st.session_state.current_img_index = 0

# --- Affichage du score et barre de progression ---
st.sidebar.metric("Score", f"{st.session_state.score} / {st.session_state.total}")
progress = 0
if st.session_state.total > 0:
    progress = int(100 * st.session_state.score / st.session_state.total)
st.sidebar.progress(progress)

# ------------------------------------------------------------
#   Partie principale : affichage des questions
# ------------------------------------------------------------
col1, col2 = st.columns([1, 2])

if st.session_state.question is not None:
    q = st.session_state.question
    mode_q = q["mode"]

    # ========================================================
    # 1) Mode "Correspondance (Famille / Genre / Espèce)"
    # ========================================================
    if mode_q == "Correspondance":
        st.markdown("### Correspondance (Famille / Genre / Espèce)")
        images_data = q["images_data"]
        corr_type = q["type_correspondance"]

        user_answers = []
        for i, item in enumerate(images_data):
            st.markdown(f"**Image n°{i+1}**")
            if item["image"]:
                st.image(item["image"], width=200)

            # Champs de saisie (selon corr_type)
            fam_ans = ""
            gen_ans = ""
            esp_ans = ""

            if ("Famille" in corr_type) or (corr_type in ["Famille & Genre", "Famille & Espèce", "Les trois (Famille, Genre, Espèce)"]):
                fam_ans = st.text_input(f"Famille - Image {i+1} :", key=f"fam_{i}")

            if ("Genre" in corr_type) or (corr_type in ["Famille & Genre", "Genre & Espèce", "Les trois (Famille, Genre, Espèce)"]):
                gen_ans = st.text_input(f"Genre - Image {i+1} :", key=f"genus_{i}")

            if ("Espèce" in corr_type) or (corr_type in ["Famille & Espèce", "Genre & Espèce", "Les trois (Famille, Genre, Espèce)"]):
                esp_ans = st.text_input(f"Espèce - Image {i+1} :", key=f"spec_{i}")

            user_answers.append((fam_ans, gen_ans, esp_ans))

        if st.button("Valider toutes les réponses"):
            feedback = ""
            correct_count = 0
            total_points = 0

            for i, item in enumerate(images_data):
                user_family, user_genus, user_species = user_answers[i]

                # Pour chaque image, on compare la (ou les) réponses
                is_family_correct = None
                is_genus_correct = None
                is_species_correct = None

                # 1) Famille ?
                if ("Famille" in corr_type) \
                   or ("Famille & Genre" in corr_type) \
                   or ("Famille & Espèce" in corr_type) \
                   or (corr_type == "Les trois (Famille, Genre, Espèce)"):
                    total_points += 1
                    if user_family.lower().strip() == item["family"].lower().strip():
                        correct_count += 1
                        is_family_correct = True
                    else:
                        is_family_correct = False

                # 2) Genre ?
                if ("Genre" in corr_type) \
                   or ("Famille & Genre" in corr_type) \
                   or ("Genre & Espèce" in corr_type) \
                   or (corr_type == "Les trois (Famille, Genre, Espèce)"):
                    total_points += 1
                    if user_genus.lower().strip() == item["genus"].lower().strip():
                        correct_count += 1
                        is_genus_correct = True
                    else:
                        is_genus_correct = False

                # 3) Espèce ?
                if ("Espèce" in corr_type) \
                   or ("Famille & Espèce" in corr_type) \
                   or ("Genre & Espèce" in corr_type) \
                   or (corr_type == "Les trois (Famille, Genre, Espèce)"):
                    total_points += 1
                    if user_species.lower().strip() == item["species"].lower().strip():
                        correct_count += 1
                        is_species_correct = True
                    else:
                        is_species_correct = False

                # Construire le feedback pour cette image
                msgs = []

                if is_family_correct is True:
                    msgs.append("Famille ✅")
                elif is_family_correct is False:
                    msgs.append(f"Famille ❌ (attendu : {item['family']})")

                if is_genus_correct is True:
                    msgs.append("Genre ✅")
                elif is_genus_correct is False:
                    msgs.append(f"Genre ❌ (attendu : {item['genus']})")

                if is_species_correct is True:
                    msgs.append("Espèce ✅")
                elif is_species_correct is False:
                    msgs.append(f"Espèce ❌ (attendu : {item['species']})")

                # Ajout du nom commun par curiosité
                msgs.append(f"Nom commun : {item['common_name']}")

                feedback += f"<p><strong>Image {i+1}</strong> :<br>{'<br>'.join(msgs)}</p>"

            st.session_state.total += total_points
            st.session_state.score += correct_count
            st.session_state.feedback = feedback
            st.markdown("### Résultats")
            st.markdown(st.session_state.feedback, unsafe_allow_html=True)

    # ========================================================
    # 2) Mode chronométré
    # ========================================================
    elif mode_q == "Mode chronométré":
        with col1:
            if "images" in q and q["images"]:
                img_url = q["images"][st.session_state.current_img_index]
                st.image(img_url, width=300)

        with col2:
            st.markdown("#### Répondez à la question (chrono)")

            # Calcul du temps restant
            elapsed = 0
            if st.session_state.start_time:
                elapsed = time.time() - st.session_state.start_time
            remaining = (st.session_state.time_limit or 30) - elapsed

            if remaining <= 0:
                st.error("Temps écoulé ! La question est perdue.")
            else:
                st.warning(f"Temps restant : {int(remaining)} s")

            family_answer = st.radio("Choisissez la famille :", q["family_choices"], key="chrono_family")
            species_answer = st.radio("Choisissez le nom scientifique :", q["species_choices"], key="chrono_species")

            if st.button("Valider"):
                # On recalcule l'écart de temps
                if st.session_state.start_time:
                    elapsed = time.time() - st.session_state.start_time

                if elapsed > (st.session_state.time_limit or 30):
                    # Trop tard
                    st.session_state.feedback = "<p class='feedback-incorrect'>⏱ Temps écoulé ! Aucune réponse enregistrée.</p>"
                else:
                    # Correction
                    feedback = ""
                    species_points = 0
                    family_points = 0

                    if family_answer == q["correct_family"]:
                        feedback += "<p class='feedback-correct'>✅ Famille correcte !</p>"
                        family_points = 1
                    else:
                        feedback += (
                            f"<p class='feedback-incorrect'>❌ Famille incorrecte ! "
                            f"La bonne réponse était: {q['correct_family']}</p>"
                        )
                    
                    if species_answer == q["correct_species"]:
                        feedback += "<p class='feedback-correct'>✅ Nom scientifique correct !</p>"
                        species_points = 1
                    else:
                        if get_genus(species_answer).lower() == get_genus(q["correct_species"]).lower():
                            feedback += (
                                f"<p class='feedback-correct'>⚠️ Genre correct, "
                                f"mais espèce incorrecte. La bonne réponse était: {q['correct_species']}</p>"
                            )
                            species_points = 0.5
                        else:
                            feedback += (
                                f"<p class='feedback-incorrect'>❌ Nom scientifique incorrect ! "
                                f"La bonne réponse était: {q['correct_species']}</p>"
                            )
                            species_points = 0

                    st.session_state.total += 2
                    st.session_state.score += (family_points + species_points)

                    feedback += f"<p>Nom commun : {q['correct_common']}</p>"
                    if q['url']:
                        feedback += f"<p>Plus d’infos : <a href='{q['url']}' target='_blank'>{q['url']}</a></p>"

                    st.session_state.feedback = feedback

                st.markdown("### Feedback")
                st.markdown(st.session_state.feedback, unsafe_allow_html=True)

    # ========================================================
    # 3) Autres modes (Facile, Difficile, etc.) + Glossaire
    # ========================================================
    else:
        # --- Cas des images (modes Facile, Difficile, etc.) ---
        if "images" in q:
            with col1:
                img_url = q["images"][st.session_state.current_img_index]
                st.image(img_url, width=300)

            with col2:
                st.markdown("#### Répondez à la question")

                # Entrainement sur le Genre ?
                if mode in ["Entrainement facile", "Entrainement difficile"] and training_type == "Genre":
                    if mode == "Entrainement facile":
                        genus_answer = st.radio("Choisissez le genre :", q.get("genus_choices", []), key="genus_radio")
                    else:
                        genus_answer = st.text_input("Entrez le genre :", key="typed_genus")

                else:
                    # Sinon, on fait l'habituel : Famille, Espèce, etc.
                    if mode in ["Facile", "Difficile", "Entrainement facile"]:
                        species_answer = st.radio("Choisissez le nom scientifique :", q.get("species_choices", []), key="species_radio")
                        if mode == "Facile":
                            family_answer = st.radio("Choisissez la famille :", q.get("family_choices", []), key="family_radio")
                        else:
                            family_answer = q["correct_family"]

                    elif mode in ["Extrêmement difficile", "Entrainement difficile"]:
                        species_answer = st.text_input("Entrez le genre et l'espèce (ex: Genus species) :", key="typed_species")
                        if mode == "Extrêmement difficile":
                            family_answer = st.text_input("Entrez la famille :", key="typed_family")
                        else:
                            family_answer = q["correct_family"]

                # Bouton Valider
                if st.button("Valider"):
                    feedback = ""

                    # Entrainement sur Genre
                    if mode in ["Entrainement facile", "Entrainement difficile"] and training_type == "Genre":
                        correct_genus = q["correct_genus"].lower().strip()
                        user_genus = genus_answer.lower().strip()

                        if user_genus == correct_genus:
                            feedback += "<p class='feedback-correct'>✅ Genre correct !</p>"
                            st.session_state.score += 1
                        else:
                            feedback += (
                                f"<p class='feedback-incorrect'>❌ Genre incorrect ! "
                                f"La bonne réponse était: {q['correct_genus']}</p>"
                            )
                        st.session_state.total += 1

                    else:
                        # Vérification du nom scientifique
                        if mode in ["Facile", "Difficile", "Entrainement facile"]:
                            if species_answer == q["correct_species"]:
                                feedback += "<p class='feedback-correct'>✅ Nom scientifique correct !</p>"
                                species_points = 1
                            else:
                                if get_genus(species_answer).lower() == get_genus(q["correct_species"]).lower():
                                    feedback += (
                                        f"<p class='feedback-correct'>⚠️ Genre correct, "
                                        f"mais espèce incorrecte. La bonne réponse était: {q['correct_species']}</p>"
                                    )
                                    species_points = 0.5
                                else:
                                    feedback += (
                                        f"<p class='feedback-incorrect'>❌ Nom scientifique incorrect ! "
                                        f"La bonne réponse était: {q['correct_species']}</p>"
                                    )
                                    species_points = 0

                            if mode == "Facile":
                                if family_answer == q["correct_family"]:
                                    feedback += "<p class='feedback-correct'>✅ Famille correcte !</p>"
                                    family_points = 1
                                else:
                                    feedback += (
                                        f"<p class='feedback-incorrect'>❌ Famille incorrecte ! "
                                        f"La bonne réponse était: {q['correct_family']}</p>"
                                    )
                                    family_points = 0
                                st.session_state.total += 2
                                st.session_state.score += (species_points + family_points)
                            else:
                                st.session_state.total += 1
                                st.session_state.score += species_points

                        elif mode in ["Extrêmement difficile", "Entrainement difficile"]:
                            user_species = species_answer.lower().strip()
                            correct_species = q["correct_species"].lower().strip()
                            if user_species == correct_species:
                                feedback += "<p class='feedback-correct'>✅ Nom scientifique correct !</p>"
                                species_points = 1
                            else:
                                if get_genus(user_species) == get_genus(correct_species):
                                    feedback += (
                                        f"<p class='feedback-correct'>⚠️ Genre correct, "
                                        f"mais espèce incorrecte. La bonne réponse était: {q['correct_species']}</p>"
                                    )
                                    species_points = 0.5
                                else:
                                    feedback += (
                                        f"<p class='feedback-incorrect'>❌ Nom scientifique incorrect ! "
                                        f"La bonne réponse était: {q['correct_species']}</p>"
                                    )
                                    species_points = 0

                            if mode == "Extrêmement difficile":
                                user_family = family_answer.lower().strip()
                                correct_family = q["correct_family"].lower().strip()
                                if user_family == correct_family:
                                    feedback += "<p class='feedback-correct'>✅ Famille correcte !</p>"
                                    family_points = 1
                                else:
                                    feedback += (
                                        f"<p class='feedback-incorrect'>❌ Famille incorrecte ! "
                                        f"La bonne réponse était: {q['correct_family']}</p>"
                                    )
                                    family_points = 0
                                st.session_state.total += 2
                                st.session_state.score += (species_points + family_points)
                            else:
                                st.session_state.total += 1
                                st.session_state.score += species_points

                    # Ajouter le feedback final sur la plante
                    feedback += f"<p>Nom commun : {q['correct_common']}</p>"
                    if q.get("taille_plante"):
                        feedback += f"<p>Taille : {q['taille_plante']}</p>"
                    if q.get("type_vegetatif"):
                        feedback += f"<p>Type végétatif : {q['type_vegetatif']}</p>"
                    if q.get("floraison"):
                        feedback += f"<p>Floraison : {q['floraison']}</p>"
                    if q.get("description"):
                        feedback += f"<p>Description : {q['description']}</p>"
                    if q.get("url"):
                        feedback += f"<p>Plus d’infos : <a href='{q['url']}' target='_blank'>{q['url']}</a></p>"

                    st.session_state.feedback = feedback
                    st.markdown("### Feedback")
                    st.markdown(st.session_state.feedback, unsafe_allow_html=True)

        # --- Cas du Glossaire ---
        elif mode_q.startswith("Glossaire"):
            # Glossaire : définition → terme
            if mode_q == "Glossaire : définition → terme":
                st.markdown("### Définition")
                st.write(q["definition"])
                if pd.notna(q["image"]) and q["image"] != "":
                    st.image(q["image"], width=600)
                user_answer = st.text_input("Quel est le terme ?", key="glossaire_answer")

            # Glossaire : terme → définition
            else:
                st.markdown("### Terme")
                st.write(q["terme"])
                if pd.notna(q["image"]) and q["image"] != "":
                    st.image(q["image"], width=600)
                user_answer = st.text_input("Quelle est la définition ?", key="glossaire_answer")
            
            if st.button("Valider"):
                if user_answer.lower().strip() == q["correct"].lower().strip():
                    st.session_state.feedback = "<p class='feedback-correct'>✅ Correct !</p>"
                else:
                    st.session_state.feedback = (
                        f"<p class='feedback-incorrect'>❌ Incorrect, la bonne réponse était : {q['correct']}</p>"
                    )
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
