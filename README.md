# IA Agent RAG

> Un système RAG (Retrieval-Augmented Generation) complet pour dialoguer avec vos documents PDF, propulsé par LlamaIndex, Qdrant, OpenAI et Inngest.

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.61-red?logo=streamlit)
![FastAPI](https://img.shields.io/badge/FastAPI-0.141-green?logo=fastapi)
![Qdrant](https://img.shields.io/badge/Qdrant-1.19-purple)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-black?logo=openai)

---

## 📖 Description

**IA Agent RAG** est un assistant conversationnel qui répond à vos questions en s'appuyant sur le contenu de vos documents PDF. Le système extrait le texte, le découpe en chunks sémantiques, génère des embeddings vectoriels, puis retrouve les passages pertinents pour formuler une réponse contextualisée avec GPT-4.

### 🎯 Fonctionnalités

- 📄 **Upload de PDF** via une interface web simple
- ✂️ **Chunking intelligent** avec LlamaIndex (chunk_size=512)
- 🔢 **Embeddings vectoriels** via OpenAI `text-embedding-3-large`
- 💾 **Stockage vectoriel** dans Qdrant (self-hosted via Docker)
- 💬 **Chat contextualisé** avec GPT-4o-mini
- 🔄 **Orchestration asynchrone** avec Inngest (retry auto, observabilité)
- 📚 **Traçabilité des sources** dans chaque réponse

---

## 🏗️ Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│  Streamlit  │─────▶│   Inngest    │─────▶│   FastAPI   │
│   (UI/UX)   │      │(Orchestrator)│      │  (Backend)  │
└─────────────┘      └──────────────┘      └──────┬──────┘
                                                   │
                    ┌──────────────────────────────┼──────────────┐
                    │                              │              │
                    ▼                              ▼              ▼
             ┌─────────────┐              ┌──────────────┐  ┌──────────┐
             │ LlamaIndex  │              │   OpenAI     │  │  Qdrant  │
             │(PDF Parser) │              │(Embed + LLM) │  │(VectorDB)│
             └─────────────┘              └──────────────┘  └──────────┘
```

### Pipeline d'ingestion (une fois par PDF)

1. **Upload** → Streamlit sauvegarde le PDF localement
2. **Event** → Envoi à Inngest (`rag/ingest_pdf`)
3. **Parse & chunk** → LlamaIndex découpe en morceaux (~512 tokens)
4. **Embed** → OpenAI génère les vecteurs (3072 dimensions)
5. **Store** → Qdrant stocke les vecteurs + métadonnées

### Pipeline de requête (à chaque question)

1. **Question** → Envoi à Inngest (`rag/query_pdf_ia`)
2. **Embed** → Vectorisation de la question
3. **Retrieval** → Recherche des top-K chunks similaires dans Qdrant
4. **Augmentation** → Construction du prompt avec le contexte
5. **Generation** → GPT-4o-mini génère la réponse

---

## 🛠️ Stack technique

| Composant | Rôle |
|---|---|
| **[Python 3.12](https://www.python.org/)** | Langage principal |
| **[uv](https://github.com/astral-sh/uv)** | Gestionnaire de paquets ultra-rapide |
| **[Streamlit](https://streamlit.io/)** | Interface utilisateur web |
| **[FastAPI](https://fastapi.tiangolo.com/)** | Serveur backend async |
| **[Inngest](https://www.inngest.com/)** | Orchestration des fonctions durables |
| **[LlamaIndex](https://www.llamaindex.ai/)** | Ingestion et découpage des documents |
| **[Qdrant](https://qdrant.tech/)** | Base de données vectorielle |
| **[OpenAI](https://openai.com/)** | Embeddings + LLM (GPT-4o-mini) |
| **[Docker](https://www.docker.com/)** | Conteneurisation de Qdrant |
| **[Pydantic](https://docs.pydantic.dev/)** | Validation des données |

---

## 📁 Structure du projet

```
IA_Agent_RAG/
├── main.py              # Serveur FastAPI + fonctions Inngest
├── streamlit_app.py     # Interface utilisateur Streamlit
├── data_loader.py       # Chargement PDF + génération d'embeddings
├── vector_db.py         # Client Qdrant (upsert, search)
├── custom_types.py      # Modèles Pydantic (contrats de données)
├── pyproject.toml       # Dépendances (uv)
├── uv.lock              # Versions verrouillées
├── .env.example         # Template des variables d'environnement
└── README.md
```

---

## 🚀 Installation

### Prérequis

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) installé
- Docker Desktop (pour Qdrant)
- Node.js (pour Inngest Dev Server)
- Une clé API OpenAI

### 1. Cloner le projet

```bash
git clone https://github.com/MAmineBrz/IA_Agent_RAG.git
cd IA_Agent_RAG
```

### 2. Installer les dépendances Python

```bash
uv sync
```

### 3. Configurer les variables d'environnement

Copie le fichier d'exemple :

```bash
cp .env.example .env
```

Puis édite `.env` et ajoute ta clé OpenAI :

```env
OPENAI_API_KEY=sk-...
```

### 4. Lancer Qdrant (base vectorielle)

Première fois :

```bash
docker run -d --name qdrant_RAG_DB -p 6333:6333 \
    -v qdrant_storage:/qdrant/storage \
    --restart unless-stopped \
    qdrant/qdrant
```

Vérifier que Qdrant tourne :

```bash
docker ps
curl http://localhost:6333/
```

Dashboard Qdrant : http://localhost:6333/dashboard

---

## ▶️ Lancement du projet

Le projet nécessite **3 processus** en parallèle. Ouvre 3 terminaux distincts.

### 🐳 Terminal 0 : Vérifier Qdrant (si déjà installé)

```bash
docker start qdrant_RAG_DB
docker ps
```

### 🚀 Terminal 1 : Serveur FastAPI (backend + fonctions Inngest)

```bash
uv run uvicorn main:app --reload
```

→ Serveur sur http://127.0.0.1:8000

### 🔄 Terminal 2 : Inngest Dev Server (orchestrateur + dashboard)

```bash
npx inngest-cli@latest dev -u http://127.0.0.1:8000/api/inngest --no-discovery
```

→ Dashboard sur http://127.0.0.1:8288

### 💻 Terminal 3 : Interface Streamlit

```bash
uv run streamlit run streamlit_app.py
```

→ Application sur http://127.0.0.1:8501

---

## 💬 Utilisation

1. Ouvre l'interface Streamlit dans ton navigateur (http://127.0.0.1:8501)
2. **Upload un PDF** via la zone dédiée
3. Attends le message *"Triggered ingestion for: nom_du_fichier.pdf"*
4. Tape ta question (ex: *"Quel est le CA de cette entreprise en 2024 ?"*)
5. Choisis le nombre de chunks à récupérer (top-K)
6. Clique sur **Ask** et attends la réponse
7. La réponse s'affiche avec les sources utilisées

### Observabilité

Le dashboard Inngest (http://127.0.0.1:8288) permet de :

- Visualiser chaque exécution de fonction
- Voir le détail de chaque step (durée, entrées, sorties)
- Rejouer manuellement une fonction
- Débugger les erreurs pas à pas

---

## ⚙️ Configuration avancée

### Modifier la taille des chunks

Dans `data_loader.py`, ajuste les paramètres du `SentenceSplitter` :

```python
splitter = SentenceSplitter(chunk_size=512, chunk_overlap=50)
```

- **chunk_size petit (256)** → recherche plus précise, plus de chunks
- **chunk_size grand (1024)** → meilleur contexte, moins de fragmentation

### Changer de modèle LLM

Dans `main.py`, fonction `_generate` :

```python
response = client.chat.completions.create(
    model="gpt-4o",  # Plus puissant que gpt-4o-mini
    ...
)
```

### Changer le modèle d'embeddings

Si tu changes le modèle d'embeddings, ajuste la dimension dans `vector_db.py` :

- `text-embedding-3-small` → dim=1536
- `text-embedding-3-large` → dim=3072 (actuel)

---

## 🐛 Résolution de problèmes

### `Connection refused` sur Qdrant

Le conteneur Docker n'est pas lancé :

```bash
docker start qdrant_RAG_DB
```

### `Unable to reach SDK URL` dans Inngest

Ton serveur uvicorn a probablement crashé. Vérifie qu'il tourne et relance-le si nécessaire.

### Réponses avec sources vides `""`

La collection Qdrant contient d'anciens chunks sans `source_id`. Nettoie et réingère :

```bash
curl -X DELETE http://localhost:6333/collections/docs
```

### Le port 8000 est déjà utilisé

Un ancien processus uvicorn tourne encore. Tue-le :

```bash
pkill -9 -f uvicorn
```

---

## 🎯 Améliorations possibles

- [ ] Historique de conversation persistant (comme ChatGPT)
- [ ] Support multi-PDF avec sélection du document à interroger
- [ ] Amélioration du prompt système (few-shot examples)
- [ ] Streaming des réponses GPT-4
- [ ] Dockerisation complète (docker-compose pour tout le stack)
- [ ] Déploiement sur Streamlit Cloud + Qdrant Cloud
- [ ] Tests unitaires et d'intégration
- [ ] Authentification utilisateur

---

## 📄 Licence

Projet personnel à but éducatif. Utilisation libre.

---

## 👤 Auteur

**Amine Barrouze** ([@MAmineBrz](https://github.com/MAmineBrz))

Projet développé dans le cadre de l'apprentissage des architectures RAG modernes.
