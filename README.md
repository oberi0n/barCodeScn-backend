# Backend de test Barcode Scanner

API REST minimale, sans base de données ni authentification, qui enregistre chaque scan en append-only dans `data/scans.log`.

## Lancement avec Docker

```bash
docker compose up -d --build
```

Le service écoute sur `0.0.0.0:8000` dans le conteneur et est publié sur le port `8000` de l'hôte. Le bind mount `./data:/data` conserve `scans.log` lors des recréations du conteneur.

Pour autoriser une ou plusieurs origines PWA, séparées par des virgules :

```bash
ALLOWED_ORIGINS="https://192.168.1.186,https://barscan.example.test" docker compose up -d --build
```

Aucune origine universelle (`*`) n'est activée par défaut. Compose autorise par défaut uniquement `https://192.168.1.186`; adaptez cette valeur à l'URL exacte de la PWA.

## Vérification

```bash
curl http://localhost:8000/healthz
```

Réponse attendue : `{"status":"ok"}`.

## Envoyer un scan depuis PowerShell Windows

```powershell
$body = @{
    barcode = "3400930001234"
    latitude = 49.123456
    longitude = 6.123456
    accuracy = 12.5
} | ConvertTo-Json

Invoke-RestMethod `
    -Uri "http://localhost:8000/scan" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

La réponse porte le statut HTTP `201 Created` et contient `status`, `barcode` et le timestamp UTC `received_at`.

Vérifiez ensuite le journal persistant :

```bash
cat data/scans.log
```

Exemple de ligne :

```text
2026-09-11T10:34:56.123Z | barcode=3400930001234 | lat=49.123456 | lon=6.123456 | accuracy=12.5m
```

`accuracy` est omis de la ligne lorsqu'il n'est pas fourni. Les lignes existantes ne sont jamais remplacées.

## Documentation API

FastAPI publie automatiquement :

- Swagger UI : <http://localhost:8000/docs>
- schéma OpenAPI : <http://localhost:8000/openapi.json>

## HTTPS, PWA et sécurité

Une PWA servie en HTTPS ne peut pas appeler directement une URL telle que `http://192.168.1.x:8000` : les navigateurs bloquent ce **mixed content**. En utilisation réelle, gardez éventuellement HTTP à l'intérieur de Docker, mais placez cette API derrière un reverse proxy HTTPS, exposez-la via le même nginx HTTPS que Barscan, ou publiez-la sous une URL HTTPS. `http://localhost:8000` reste adapté aux tests locaux avec curl.

Cette première version ne possède **aucune authentification**. Elle est réservée aux tests et à un réseau contrôlé et **ne doit pas être exposée directement sur Internet** en l'état.

## Développement et tests

Avec Python 3.12 :

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
```

Variables disponibles :

| Variable | Valeur par défaut | Rôle |
| --- | --- | --- |
| `ALLOWED_ORIGINS` | vide dans Python, `https://192.168.1.186` via Compose | Origines CORS séparées par des virgules |
| `SCANS_LOG_PATH` | `/data/scans.log` | Emplacement du journal (notamment utile aux tests) |
| `LOG_LEVEL` | `INFO` | Niveau de journalisation Python |
