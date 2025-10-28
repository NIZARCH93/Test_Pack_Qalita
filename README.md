# pack_sales_quality

Pack QALITA for basic sales data quality checks.

## Contenu
- main.py : logique du pack (not-null, montant > 0, statuts valides, doublons)
- properties.yaml : métadonnées du pack
- pack_conf.json : configuration d'exemple
- requirements.txt : dépendances
- sample_data/sales_data.csv : jeu d'exemple

## Exécution locale (exemple)
1. Installer les dépendances :
   pip install -r requirements.txt

2. Lancer (si tu utilises directement QALITA CLI, adapte la commande) :
   python main.py

Note: selon ton environnement QALITA, le pack peut être exécuté via `qalita run` ou `poetry run python main.py`.
