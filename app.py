"""Dashboard de Supervision Technique - Interface Streamlit Interactive.

Supervision des flux DSI, alertes, incidents et avancement des projets
alimenté par Gmail API, Google Chat API, Gemini 1.5 Pro et Supabase.
"""

import datetime
import json
import os
import pandas as pd
import plotly.express as px
import streamlit as st

from backend.mock_data import MOCK_STRUCTURED_SUMMARY
from backend.supabase_client import (
    get_available_dates,
    get_latest_report,
    get_report_by_date,
    get_supabase_client,
    upsert_daily_report,
)

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Supervision Technique SI | Gemini & Supabase",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Injection de styles CSS personnalisés pour une esthétique moderne et soignée
st.markdown(
    """
    <style>
        /* Import typographie moderne */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        /* En-tête de page */
        .main-header {
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            padding: 24px 30px;
            border-radius: 14px;
            color: white;
            margin-bottom: 25px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
            border: 1px solid rgba(255, 255, 255, 0.08);
        }
        .main-header h1 {
            margin: 0;
            font-size: 1.85rem;
            font-weight: 700;
            letter-spacing: -0.5px;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .main-header p {
            margin: 8px 0 0 0;
            color: #94a3b8;
            font-size: 0.95rem;
        }

        /* Cartes KPI */
        .kpi-card {
            background: #ffffff;
            border-radius: 12px;
            padding: 18px 22px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .kpi-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(0,0,0,0.08);
        }
        .kpi-title {
            color: #64748b;
            font-size: 0.82rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .kpi-value {
            font-size: 2rem;
            font-weight: 700;
            margin: 4px 0;
            color: #0f172a;
        }

        /* Badges de Statut */
        .status-badge {
            display: inline-flex;
            align-items: center;
            padding: 4px 12px;
            border-radius: 9999px;
            font-size: 0.8rem;
            font-weight: 600;
            gap: 6px;
        }
        .status-resolu {
            background-color: #ecfdf5;
            color: #047857;
            border: 1px solid #a7f3d0;
        }
        .status-encours {
            background-color: #fffbeb;
            color: #b45309;
            border: 1px solid #fde68a;
        }
        .status-alerte {
            background-color: #fef2f2;
            color: #b91c1c;
            border: 1px solid #fecaca;
        }

        /* Cartes d'alerte */
        .alert-item {
            background: #fef2f2;
            border-left: 4px solid #ef4444;
            padding: 14px 18px;
            border-radius: 0 8px 8px 0;
            margin-bottom: 12px;
            color: #991b1b;
            font-size: 0.95rem;
            display: flex;
            align-items: flex-start;
            gap: 12px;
        }

        /* Tags BDD & Flux */
        .tech-tag {
            display: inline-block;
            background: #f1f5f9;
            color: #475569;
            padding: 2px 8px;
            border-radius: 6px;
            font-size: 0.78rem;
            font-weight: 500;
            font-family: monospace;
            border: 1px solid #e2e8f0;
            margin-right: 6px;
            margin-bottom: 4px;
        }

        /* Bloc Solution Technique */
        .tech-solution {
            background: #f8fafc;
            border-radius: 8px;
            padding: 14px;
            border: 1px solid #e2e8f0;
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 0.88rem;
            color: #0f172a;
            white-space: pre-wrap;
            margin-top: 8px;
        }

        /* Résumé Exécutif Callout */
        .executive-summary {
            background: #f0fdf4;
            border: 1px solid #bbf7d0;
            border-radius: 10px;
            padding: 18px 22px;
            color: #166534;
            font-size: 1rem;
            line-height: 1.6;
            margin-bottom: 25px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# --- 1. En-tête Principal ---
st.markdown(
    """
    <div class="main-header">
        <h1>⚡ Supervision Technique SI & Flux Opérationnels</h1>
        <p>Agrégation temps réel Gmail & Google Chat • Analyse IA Gemini 1.5 Pro • Historique Supabase</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# --- 2. Barre Latérale (Sidebar) : Connexion, Date & Filtres ---
with st.sidebar:
    st.header("⚙️ Paramètres & Filtres")

    # Vérification du statut de connexion Supabase
    supabase_client = get_supabase_client()
    if supabase_client:
        st.success("🟢 Connecté à Supabase", icon="✅")
    else:
        st.warning("🟠 Mode Déconnecté (Supabase hors-ligne)", icon="⚠️")

    # Sélection de la date
    available_dates = get_available_dates()
    selected_date_str = None

    if available_dates:
        selected_date_str = st.selectbox(
            "📅 Date du Rapport :",
            options=available_dates,
            index=0,
            help="Sélectionnez une date parmi l'historique disponible dans Supabase.",
        )
    else:
        today_default = datetime.date.today().isoformat()
        st.info("Aucune date en base. Utilisation de la date du jour.")
        selected_date_str = str(
            st.date_input("📅 Date du Rapport :", datetime.date.today())
        )

    st.divider()
    st.subheader("🔍 Filtres Dynamiques")

    # Filtre par statut d'incident
    status_filter = st.radio(
        "Statut des Incidents :",
        options=["Tous", "En cours", "Résolu"],
        index=0,
        horizontal=True,
    )

    # Bouton de rafraîchissement manuel
    st.divider()
    if st.button("🔄 Rafraîchir les données", use_container_width=True):
        st.rerun()

    # Injection directe de données d'exemple (très utile pour premier test)
    with st.expander("🛠️ Actions Administrateur"):
        if st.button("📥 Charger les données de démo dans Supabase"):
            today_str = datetime.date.today().isoformat()
            try:
                upsert_daily_report(today_str, MOCK_STRUCTURED_SUMMARY)
                st.success(f"Données de démo injectées pour le {today_str} !")
                st.rerun()
            except Exception as ex:
                st.error(f"Erreur d'injection : {ex}")


# --- 3. Récupération des Données du Rapport Sélectionné ---
current_report = None
if selected_date_str and supabase_client:
    current_report = get_report_by_date(selected_date_str)

# Fallback si Supabase est vide ou non connecté
if not current_report:
    if not available_dates:
        st.warning(
            "⚠️ Aucun rapport n'a été trouvé dans votre base de données Supabase pour cette date.\n\n"
            "👉 Cliquez sur **'Charger les données de démo dans Supabase'** dans la barre latérale "
            "ou lancez la commande `python backend/daily_runner.py --mock` pour initialiser la base."
        )
        # Affichage direct du mock pour offrir une prévisualisation immédiate
        current_report = {
            "report_date": selected_date_str or datetime.date.today().isoformat(),
            "raw_summary": MOCK_STRUCTURED_SUMMARY,
        }
    else:
        st.info(f"Aucun enregistrement pour la date {selected_date_str}.")
        st.stop()

raw_summary = current_report.get("raw_summary", {})
if isinstance(raw_summary, str):
    try:
        raw_summary = json.loads(raw_summary)
    except Exception:
        raw_summary = {}

statut_global = raw_summary.get("statut_global", "Vert")
resume_executif = raw_summary.get("resume_executif", "Aucun résumé disponible.")
alertes = raw_summary.get("alertes", [])
incidents = raw_summary.get("incidents", [])
projets = raw_summary.get("projets", [])


# --- 4. Extraction dynamique des filtres BDD, Flux & Projets ---
all_bdds = set()
all_flux = set()
for inc in incidents:
    for b in inc.get("bdd_impactees", []):
        if b:
            all_bdds.add(b)
    for f in inc.get("flux_impactes", []):
        if f:
            all_flux.add(f)

with st.sidebar:
    selected_bdds = st.multiselect(
        "Bases de Données :",
        options=sorted(list(all_bdds)),
        help="Filtrer par BDD ou schéma impacté",
    )
    selected_flux = st.multiselect(
        "Flux / Jobs :",
        options=sorted(list(all_flux)),
        help="Filtrer par flux de données ou ordonnancement",
    )
    all_projects_names = [p.get("nom_projet") for p in projets if p.get("nom_projet")]
    selected_project = st.selectbox(
        "Filtrer par Projet :",
        options=["Tous les projets"] + sorted(all_projects_names),
        index=0,
    )


# --- 5. Navigation par Onglets ---
tab1, tab2, tab3 = st.tabs(
    [
        "📊 Vue d'ensemble & Alertes",
        "🚨 Incidents & Résolutions Techniques",
        "🚀 Avancement par Projet",
    ]
)


# ==============================================================================
# ONGLET 1 : VUE D'ENSEMBLE & ALERTES
# ==============================================================================
with tab1:
    # 1. Résumé Exécutif
    st.markdown(
        f"""
        <div class="executive-summary">
            <strong>📋 Synthèse Exécutive ({selected_date_str}) :</strong><br>
            {resume_executif}
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 2. Cartes KPI
    col1, col2, col3, col4, col5 = st.columns(5)

    total_incidents = len(incidents)
    incidents_resolus = sum(1 for i in incidents if i.get("statut") == "Résolu")
    incidents_en_cours = total_incidents - incidents_resolus

    statut_colors = {
        "Vert": ("🟢 Nominal", "#ecfdf5", "#047857"),
        "Orange": ("🟠 Dégradé", "#fffbeb", "#b45309"),
        "Rouge": ("🔴 Critique", "#fef2f2", "#b91c1c"),
    }
    label_status, bg_stat, col_stat = statut_colors.get(
        statut_global, ("⚪ Inconnu", "#f1f5f9", "#475569")
    )

    with col1:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-title">Santé Globale SI</div>
                <div class="kpi-value" style="font-size: 1.4rem; color: {col_stat};">{label_status}</div>
                <span style="font-size: 0.8rem; color: #64748b;">Flux DSI & Intégrations</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-title">Alertes Majeures</div>
                <div class="kpi-value" style="color: #dc2626;">{len(alertes)}</div>
                <span style="font-size: 0.8rem; color: #64748b;">Points de vigilance</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-title">Incidents Totaux</div>
                <div class="kpi-value">{total_incidents}</div>
                <span style="font-size: 0.8rem; color: #64748b;">Sur les dernières 24h</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col4:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-title">Incidents Résolus</div>
                <div class="kpi-value" style="color: #059669;">{incidents_resolus}</div>
                <span style="font-size: 0.8rem; color: #64748b;">Taux : {int((incidents_resolus/total_incidents)*100) if total_incidents else 100}%</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col5:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-title">Projets Actifs</div>
                <div class="kpi-value" style="color: #2563eb;">{len(projets)}</div>
                <span style="font-size: 0.8rem; color: #64748b;">OneStock, DSI, Stambia...</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # 3. Section des Alertes Majeures du Jour
    st.subheader("⚠️ Alertes & Points de Vigilance Critiques")
    if alertes:
        for alerte in alertes:
            st.markdown(
                f"""
                <div class="alert-item">
                    <span style="font-size: 1.2rem;">🚨</span>
                    <div>{alerte}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.success("Aucune alerte critique enregistrée pour cette journée.")

    # 4. Graphiques d'impact (Plotly)
    if incidents:
        st.markdown("<br>", unsafe_allow_html=True)
        col_g1, col_g2 = st.columns(2)

        with col_g1:
            st.markdown("##### 📌 Répartition des Statuts")
            df_status = pd.DataFrame(
                [
                    {"Statut": "Résolu", "Nombre": incidents_resolus},
                    {"Statut": "En cours", "Nombre": incidents_en_cours},
                ]
            )
            fig_pie = px.pie(
                df_status,
                names="Statut",
                values="Nombre",
                color="Statut",
                color_discrete_map={"Résolu": "#10b981", "En cours": "#f59e0b"},
                hole=0.45,
            )
            fig_pie.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=260)
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_g2:
            st.markdown("##### 🗄️ Principales Bases de Données Impactées")
            bdd_counts = {}
            for inc in incidents:
                for b in inc.get("bdd_impactees", []):
                    bdd_counts[b] = bdd_counts.get(b, 0) + 1

            if bdd_counts:
                df_bdd = pd.DataFrame(
                    list(bdd_counts.items()), columns=["Base de Données", "Incidents"]
                ).sort_values("Incidents", ascending=True)
                fig_bar = px.bar(
                    df_bdd,
                    x="Incidents",
                    y="Base de Données",
                    orientation="h",
                    color_discrete_sequence=["#3b82f6"],
                )
                fig_bar.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=260)
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("Aucune base spécifique n'est référencée.")


# ==============================================================================
# ONGLET 2 : INCIDENTS & RÉSOLUTIONS TECHNIQUES
# ==============================================================================
with tab2:
    st.subheader("🛠️ Registre Détaillé des Incidents")

    # Moteur de recherche textuel
    search_query = st.text_input(
        "🔍 Rechercher dans les incidents :",
        placeholder="Tapez un mot-clé (ex: OneStock, ORA-00001, timeout, index, Stambia, pool...)",
    )

    # Filtrage des incidents
    filtered_incidents = []
    for inc in incidents:
        # Filtre Statut
        if status_filter != "Tous" and inc.get("statut") != status_filter:
            continue

        # Filtre BDD
        if selected_bdds:
            inc_bdds = inc.get("bdd_impactees", [])
            if not any(b in inc_bdds for b in selected_bdds):
                continue

        # Filtre Flux
        if selected_flux:
            inc_flux = inc.get("flux_impactes", [])
            if not any(f in inc_flux for f in selected_flux):
                continue

        # Recherche textuelle plein texte
        if search_query:
            q = search_query.lower()
            text_to_search = " ".join(
                [
                    inc.get("titre", ""),
                    inc.get("description", ""),
                    inc.get("cause_racine", ""),
                    inc.get("solution_technique", ""),
                    " ".join(inc.get("bdd_impactees", [])),
                    " ".join(inc.get("flux_impactes", [])),
                ]
            ).lower()
            if q not in text_to_search:
                continue

        filtered_incidents.append(inc)

    st.write(f"Affichage de **{len(filtered_incidents)}** incident(s) sur {len(incidents)}.")

    if not filtered_incidents:
        st.info("Aucun incident ne correspond à vos critères de recherche.")
    else:
        for idx, inc in enumerate(filtered_incidents, start=1):
            is_resolu = inc.get("statut") == "Résolu"
            badge_class = "status-resolu" if is_resolu else "status-encours"
            badge_icon = "✓ Résolu" if is_resolu else "⏳ En cours"

            with st.container():
                st.markdown(
                    f"""
                    <div style="background: white; border-radius: 10px; border: 1px solid #e2e8f0; padding: 18px; margin-bottom: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.03);">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px;">
                            <h4 style="margin: 0; color: #0f172a; font-size: 1.1rem;">#{idx}. {inc.get('titre', 'Incident sans titre')}</h4>
                            <span class="status-badge {badge_class}">{badge_icon}</span>
                        </div>
                        <p style="color: #475569; font-size: 0.95rem; margin-bottom: 12px;">{inc.get('description', '')}</p>
                    """,
                    unsafe_allow_html=True,
                )

                # Tags BDD & Flux
                bdds = inc.get("bdd_impactees", [])
                flux_list = inc.get("flux_impactes", [])

                col_meta1, col_meta2 = st.columns([1, 1])
                with col_meta1:
                    if bdds:
                        tags_html = "".join([f'<span class="tech-tag">🗄️ {b}</span>' for b in bdds])
                        st.markdown(f"**BDD Impactées :** {tags_html}", unsafe_allow_html=True)
                with col_meta2:
                    if flux_list:
                        tags_flux = "".join([f'<span class="tech-tag">🔄 {f}</span>' for f in flux_list])
                        st.markdown(f"**Flux Impactés :** {tags_flux}", unsafe_allow_html=True)

                # Cause Racine et Solution Technique
                st.markdown(
                    f"""
                    <div style="margin-top: 10px;">
                        <strong style="color: #b91c1c;">🎯 Cause Racine Identifiée :</strong><br>
                        <span style="color: #334155;">{inc.get('cause_racine', 'Non précisée')}</span>
                    </div>
                    <div style="margin-top: 10px;">
                        <strong style="color: #047857;">💡 Solution Technique Appliquée / Action :</strong>
                        <div class="tech-solution">{inc.get('solution_technique', 'En attente d intervention')}</div>
                    </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        # Possibilité d'export CSV
        st.markdown("<br>", unsafe_allow_html=True)
        export_df = pd.DataFrame(filtered_incidents)
        csv_data = export_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Exporter ces incidents au format CSV",
            data=csv_data,
            file_name=f"incidents_supervision_{selected_date_str}.csv",
            mime="text/csv",
        )


# ==============================================================================
# ONGLET 3 : AVANCEMENT PAR PROJET
# ==============================================================================
with tab3:
    st.subheader("🚀 Projets, Réalisations & Décisions Techniques")

    # Filtrage éventuel par projet
    filtered_projets = projets
    if selected_project != "Tous les projets":
        filtered_projets = [p for p in projets if p.get("nom_projet") == selected_project]

    if not filtered_projets:
        st.info("Aucun projet répertorié pour cette sélection.")
    else:
        for p in filtered_projets:
            nom_projet = p.get("nom_projet", "Projet sans nom")
            libelle = p.get("libelle", "Général")
            actions = p.get("actions_realisees", [])
            decisions = p.get("decisions", [])

            with st.expander(f"📁 {nom_projet} ({libelle})", expanded=True):
                col_act, col_dec = st.columns([1.2, 1])

                with col_act:
                    st.markdown("##### ✅ Actions Réalisées (Dernières 24h)")
                    if actions:
                        for act in actions:
                            st.markdown(f"- {act}")
                    else:
                        st.markdown("*Aucune action spécifique consignée.*")

                with col_dec:
                    st.markdown("##### 📌 Décisions & Prochains Jalons")
                    if decisions:
                        for dec in decisions:
                            st.markdown(
                                f"""
                                <div style="background: #eff6ff; border-left: 3px solid #3b82f6; padding: 10px 14px; border-radius: 4px; margin-bottom: 8px; font-size: 0.9rem; color: #1e40af;">
                                    {dec}
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                    else:
                        st.markdown("*Aucune décision arbitrée.*")


# --- Footer ---
st.markdown("<br><hr>", unsafe_allow_html=True)
st.markdown(
    """
    <div style="text-align: center; color: #94a3b8; font-size: 0.85rem;">
        Dashboard de Supervision Technique • Propulsé par Streamlit, Gemini 1.5 Pro, Google Workspace & Supabase
    </div>
    """,
    unsafe_allow_html=True,
)
