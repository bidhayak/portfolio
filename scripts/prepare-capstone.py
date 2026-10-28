"""Package the user's original capstone and extract its unchanged ranking code."""
import ast
from pathlib import Path
import sys
import zipfile

source = Path(sys.argv[1]).resolve()
root = Path(__file__).resolve().parents[1]
target = root / 'dist' / 'projects' / 'job-recommender'
target.mkdir(parents=True, exist_ok=True)
text = (source / 'job_recommender.py').read_text(encoding='utf-8-sig')
tree = ast.parse(text)
names = {'ModelSettings', 'KNOWN_SKILLS', 'clean_text', 'extract_known_skills', 'find_column', 'prepare_job_data', 'infer_job_source', 'JobRecommendationModel'}
segments = []
for node in tree.body:
    name = getattr(node, 'name', None)
    assigned = [t.id for t in getattr(node, 'targets', []) if isinstance(t, ast.Name)]
    if name in names or any(n in names or n.startswith('JOB_') for n in assigned):
        start = min([node.lineno] + [d.lineno for d in getattr(node, 'decorator_list', [])]) - 1
        segments.append('\n'.join(text.splitlines()[start:node.end_lineno]))
header = '''# Extracted verbatim from Bidhayak Baral's capstone ranking engine.
# Browser adapter and UI are separate; the original Streamlit project is downloadable.
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Optional
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

'''
engine = header + '\n\n\n'.join(segments) + '\n'
compile(engine, 'engine.py', 'exec')
(target / 'engine.py').write_text(engine, encoding='utf-8')

files = ['app.py', 'job_recommender.py', 'evaluation.py', 'job_sources.py', 'start_app.bat']
for filename in files:
    code = (source / filename).read_text(encoding='utf-8-sig')
    if filename.endswith('.py'):
        for node in ast.walk(ast.parse(code)):
            if isinstance(node, (ast.Assign, ast.AnnAssign)) and isinstance(getattr(node, 'value', None), ast.Constant):
                value = node.value.value
                ids = [n.id.lower() for n in ast.walk(node) if isinstance(n, ast.Name)]
                if isinstance(value, str) and len(value) > 12 and any(any(k in n for k in ('password', 'secret', 'api_key', 'authorization_key', 'access_token')) for n in ids):
                    raise ValueError(f'Review a possible hardcoded credential in {filename}:{node.lineno} before packaging.')

requirements = '''streamlit>=1.55,<2
pandas>=2.1,<3
numpy>=1.26,<3
scikit-learn>=1.4,<2
matplotlib>=3.8,<4
pypdf>=4,<7
python-docx>=1.1,<2
openpyxl>=3.1,<4
xlrd>=2,<3
'''
readme = '''# AI-Based Job Recommendation System

Bidhayak Baral — Data Science Capstone, 2026

This archive contains the original Streamlit application, TF-IDF recommendation
engine, job-source adapters, and human-judgment evaluation code. Private resume
submissions, API keys, caches, and source datasets are excluded.

## Run the full application

Install Python 3.11 or newer. From this folder:

    python -m venv .venv
    # Activate the environment, then:
    python -m pip install -r requirements.txt
    python -m streamlit run app.py

On Windows, start_app.bat can create the environment and launch the app.

Use your own job CSV and resume, or configure the supported job APIs in the app.
Obtain any required API credentials from the providers and enter them locally.
No credentials are included in this archive.

## Method

The engine normalizes text, weights job titles twice, uses unigram/bigram TF-IDF,
and ranks by cosine similarity. Shared terms, matched skills, and missing skills
explain the results. Skill explanations do not change the cosine ranking.

The evaluation module calculates Precision@K, nDCG@K, and mean reciprocal rank
from human relevance judgments. No accuracy or hiring-success rate is claimed.

## Browser edition

The portfolio's browser edition executes extracted, unchanged ranking classes
and helpers in Pyodide. It adds a lightweight web interface, example roles,
text-resume input, and optional job CSV input. Its small-corpus configuration
uses min_df=1 and max_df=1.0. The full Streamlit interface and live job API
integrations are available when running this original project locally.
'''
download = root / 'dist' / 'downloads'
download.mkdir(exist_ok=True)
with zipfile.ZipFile(download / 'job-recommendation-system.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
    for filename in files:
        archive.write(source / filename, 'job-recommendation-system/' + filename)
    archive.writestr('job-recommendation-system/requirements.txt', requirements)
    archive.writestr('job-recommendation-system/README.md', readme)
print(f'Extracted {len(segments)} original definitions; packaged {len(files)} original source files.')
