# pack_sales_quality

Pack QALITA pour vérifier quelques règles de qualité simples sur des données de commandes.

## Contenu

- `main.py` : logique du pack (présence des colonnes clés, valeurs nulles, montants positifs, statuts valides, doublons, score synthétique).
- `properties.yaml` : métadonnées du pack pour QALITA (identité, description, tags).
- `pack_conf.json` : configuration d'exemple pour exécuter le pack en local avec le CLI QALITA.
- `requirements.txt` : dépendances Python nécessaires pour exécuter le pack.
- `sample_data/reference_sales_data.csv` : échantillon de données "référence" propre.
- `sample_data/current_sales_data.csv` : échantillon de données "cible" avec quelques anomalies pour illustrer les métriques.

## Utilisation

1. Installez les dépendances :
   ```bash
   pip install -r requirements.txt
   ```
2. Exécutez le pack avec le CLI QALITA, par exemple :
   ```bash
   qalita pack run --pack-path . --config pack_conf.json
   ```

Le pack charge les données indiquées dans la configuration et publie les métriques dans le dossier de sortie défini par QALITA.
