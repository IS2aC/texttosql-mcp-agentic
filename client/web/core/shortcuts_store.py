# client/web/core/shortcuts_store.py
"""
Stockage local des raccourcis d'analyse (CSV).
Colonnes : id_raccourci, name, libelle

- id_raccourci : identifiant unique (uuid4)
- name         : intitulé court affiché sur le bouton (ex: "Top 5 produits")
- libelle      : texte complet envoyé au chat (ex: "Quels sont les 5 produits les plus vendus ?")
"""
import os
import csv
import uuid
from loguru import logger

CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "shortcuts.csv")
FIELDNAMES = ["id_raccourci", "name", "libelle"]


def _ensure_file():
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()


def list_shortcuts() -> list[dict]:
    """Retourne la liste des raccourcis enregistrés."""
    _ensure_file()
    with open(CSV_PATH, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [row for row in reader]


def add_shortcut(name: str, libelle: str) -> dict:
    """Ajoute un nouveau raccourci et retourne son enregistrement."""
    _ensure_file()
    name = name.strip()
    libelle = libelle.strip()

    if not name or not libelle:
        raise ValueError("Le nom et l'intitulé sont obligatoires.")

    record = {
        "id_raccourci": str(uuid.uuid4()),
        "name": name,
        "libelle": libelle,
    }

    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writerow(record)

    logger.info(f"[shortcuts] Ajouté : {record['id_raccourci'][:8]} → '{name}'")
    return record


def delete_shortcut(id_raccourci: str) -> bool:
    """Supprime un raccourci par son id. Retourne True si trouvé et supprimé."""
    _ensure_file()
    rows = list_shortcuts()
    new_rows = [r for r in rows if r["id_raccourci"] != id_raccourci]

    if len(new_rows) == len(rows):
        return False  # rien supprimé

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(new_rows)

    logger.info(f"[shortcuts] Supprimé : {id_raccourci[:8]}")
    return True