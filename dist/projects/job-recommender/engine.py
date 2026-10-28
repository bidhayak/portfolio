# Extracted verbatim from Bidhayak Baral's capstone ranking engine.
# Browser adapter and UI are separate; the original Streamlit project is downloadable.
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Optional
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

@dataclass(frozen=True)
class ModelSettings:
    """Storing reproducible limits and TF-IDF settings."""

    max_resumes: int = 500
    max_jobs: int = 10000
    top_n: int = 10
    random_state: int = 42
    max_features: int = 50000
    min_df: int = 2
    max_df: float = 0.95
    ngram_min: int = 1
    ngram_max: int = 2


JOB_ID_COLUMNS = ["job_id", "jobid", "id"]


JOB_TITLE_COLUMNS = ["title", "job_title", "name"]


JOB_DESCRIPTION_COLUMNS = ["description", "job_description", "details", "content"]


JOB_SKILLS_COLUMNS = ["skills_desc", "skills", "skill", "required_skills"]


JOB_LOCATION_COLUMNS = ["location", "job_location", "city"]


JOB_COMPANY_COLUMNS = ["company_name", "company", "organization"]


JOB_URL_COLUMNS = [
    "job_posting_url",
    "application_url",
    "job_url",
    "posting_url",
    "apply_url",
    "url",
]


JOB_SOURCE_COLUMNS = ["source", "job_source", "job_board", "platform", "site", "_input_source"]


JOB_POSTED_COLUMNS = ["posted_at", "created", "listed_time", "original_listed_time", "date_posted"]


JOB_EXPIRES_COLUMNS = ["expires_at", "expiry", "application_close_date", "closed_at"]


KNOWN_SKILLS = {
    ".net",
    "agile",
    "airflow",
    "angular",
    "ansible",
    "apache spark",
    "aws",
    "azure",
    "c#",
    "c++",
    "cassandra",
    "ci/cd",
    "computer vision",
    "css",
    "data analysis",
    "data engineering",
    "data visualization",
    "deep learning",
    "django",
    "docker",
    "excel",
    "fastapi",
    "flask",
    "gcp",
    "git",
    "github",
    "hadoop",
    "html",
    "java",
    "javascript",
    "jenkins",
    "jira",
    "kafka",
    "keras",
    "kubernetes",
    "linux",
    "machine learning",
    "matplotlib",
    "mongodb",
    "mysql",
    "natural language processing",
    "nlp",
    "node.js",
    "nosql",
    "numpy",
    "pandas",
    "plotly",
    "postgresql",
    "power bi",
    "python",
    "pytorch",
    "r",
    "react",
    "rest api",
    "sas",
    "scikit-learn",
    "scrum",
    "seaborn",
    "snowflake",
    "spark",
    "sql",
    "sqlite",
    "tableau",
    "tensorflow",
    "terraform",
    "typescript",
    "unix",
    "visual basic",
    "vue",
}


def clean_text(value: object) -> str:
    """Cleaning text while preserving common technology symbols."""

    # Converting missing values into empty strings before applying regular expressions
    text = "" if pd.isna(value) else str(value)
    # Removing markup and web addresses because they do not describe applicant-job fit
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    # Normalizing case while retaining symbols used by skills such as C++, C#, and .NET
    text = text.lower()
    text = re.sub(r"[^a-z0-9+#./\- ]+", " ", text)
    # Collapsing repeated spaces into one consistent token boundary
    return re.sub(r"\s+", " ", text).strip()


def extract_known_skills(value: object) -> set[str]:
    """Extracting recognizable technical skills with literal boundary-aware matching."""

    # Padding cleaned text so skills at the beginning and end receive boundaries
    text = f" {clean_text(value)} "
    found: set[str] = set()
    for skill in KNOWN_SKILLS:
        # Escaping punctuation while allowing flexible spaces inside multi-word skills
        escaped = re.escape(skill).replace(r"\ ", r"\s+")
        if re.search(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", text, flags=re.IGNORECASE):
            found.add(skill)
    # Removing shorter aliases when a more descriptive version is already present
    if "natural language processing" in found:
        found.discard("nlp")
    if "apache spark" in found:
        found.discard("spark")
    return found


def find_column(dataframe: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    """Finding the first matching column without depending on capitalization."""

    # Creating a lowercase lookup while preserving each table's original column spelling
    lookup = {str(column).strip().lower(): str(column) for column in dataframe.columns}
    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]
    return None


def prepare_job_data(job_raw: pd.DataFrame) -> pd.DataFrame:
    """Standardizing and cleaning job records for vectorization."""

    # Resolving each optional and required field across common job-table schemas
    job_id_column = find_column(job_raw, JOB_ID_COLUMNS)
    title_column = find_column(job_raw, JOB_TITLE_COLUMNS)
    description_column = find_column(job_raw, JOB_DESCRIPTION_COLUMNS)
    skills_column = find_column(job_raw, JOB_SKILLS_COLUMNS)
    location_column = find_column(job_raw, JOB_LOCATION_COLUMNS)
    company_column = find_column(job_raw, JOB_COMPANY_COLUMNS)
    url_column = find_column(job_raw, JOB_URL_COLUMNS)
    source_column = find_column(job_raw, JOB_SOURCE_COLUMNS)
    posted_column = find_column(job_raw, JOB_POSTED_COLUMNS)
    expires_column = find_column(job_raw, JOB_EXPIRES_COLUMNS)

    if title_column is None or description_column is None:
        raise KeyError("Job title and description columns are required in the selected job table.")

    def values_or_default(column: Optional[str], default: str = "") -> pd.Series:
        """Returning cleaned string values or a repeated default value."""

        if column is None:
            return pd.Series(default, index=job_raw.index, dtype="object")
        return job_raw[column].fillna(default).astype(str)

    # Building a consistent internal job schema without mutating the original input
    job_data = pd.DataFrame(
        {
            "job_id": values_or_default(job_id_column),
            "job_title": values_or_default(title_column, "Untitled Job"),
            "job_description_raw": values_or_default(description_column),
            "job_skills": values_or_default(skills_column),
            "job_location": values_or_default(location_column),
            "job_company": values_or_default(company_column, "Not provided"),
            "job_url": values_or_default(url_column),
            "job_source": values_or_default(source_column, "Local dataset"),
            "job_posted_at": values_or_default(posted_column),
            "job_expires_at": values_or_default(expires_column),
        }
    )
    # Assigning stable local identifiers when a source omits job IDs
    missing_ids = job_data["job_id"].str.strip().eq("")
    job_data.loc[missing_ids, "job_id"] = job_data.index[missing_ids].map(lambda value: f"local_{value}")

    # Inferring recognizable job-board names from available listing links
    inferred_sources = job_data["job_url"].map(infer_job_source)
    missing_sources = job_data["job_source"].str.strip().isin(["", "Local dataset"])
    job_data.loc[missing_sources & inferred_sources.ne(""), "job_source"] = inferred_sources

    # Building LinkedIn listing links when the dataset only provides numeric job identifiers
    linkedin_rows = job_data["job_source"].str.contains("linkedin", case=False, na=False)
    numeric_ids = job_data["job_id"].str.fullmatch(r"\d+", na=False)
    missing_urls = job_data["job_url"].str.strip().eq("")
    fallback_rows = linkedin_rows & numeric_ids & missing_urls
    job_data.loc[fallback_rows, "job_url"] = (
        "https://www.linkedin.com/jobs/view/" + job_data.loc[fallback_rows, "job_id"]
    )

    # Weighting titles twice while combining the available job text fields
    job_data["job_document_raw"] = (
        job_data["job_title"]
        + " "
        + job_data["job_title"]
        + " "
        + job_data["job_description_raw"]
        + " "
        + job_data["job_skills"]
    )
    # Cleaning combined documents before dropping unusable or exact duplicate text
    job_data["job_document"] = job_data["job_document_raw"].map(clean_text)
    job_data = job_data[job_data["job_document"].str.len() >= 30]
    job_data = job_data.drop_duplicates("job_document").reset_index(drop=True)
    if job_data.empty:
        raise ValueError("No usable job records remained after text cleaning.")
    return job_data


def infer_job_source(url: object) -> str:
    """Inferring a job-board label from a listing URL."""

    # Normalizing URL case before checking recognizable public job-board domains
    normalized_url = str(url).lower()
    known_sources = {
        "linkedin.com": "LinkedIn",
        "indeed.com": "Indeed",
        "glassdoor.com": "Glassdoor",
        "ziprecruiter.com": "ZipRecruiter",
        "monster.com": "Monster",
        "dice.com": "Dice",
    }
    for domain, source in known_sources.items():
        if domain in normalized_url:
            return source
    return ""


class JobRecommendationModel:
    """Building and applying the TF-IDF cosine-similarity model."""

    def __init__(self, settings: ModelSettings) -> None:
        """Initializing model storage before fitting the vectorizer."""

        # Retaining settings so exported run details can reproduce the vectorizer
        self.settings = settings
        # Configuring explainable word and phrase features with sublinear term frequency
        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(settings.ngram_min, settings.ngram_max),
            min_df=settings.min_df,
            max_df=settings.max_df,
            sublinear_tf=True,
            max_features=settings.max_features,
        )
        # Initializing fitted data and sparse-vector holders as empty state
        self.resume_data: Optional[pd.DataFrame] = None
        self.job_data: Optional[pd.DataFrame] = None
        self.resume_vectors = None
        self.job_vectors = None
        self.query_text = ""

    def fit(self, resume_data: pd.DataFrame, job_data: pd.DataFrame) -> None:
        """Fitting one shared vocabulary across resume and job documents."""

        # Combining resume and job documents so inverse-document frequencies share one corpus
        all_documents = pd.concat(
            [resume_data["resume_text"], job_data["job_document"]],
            ignore_index=True,
        )
        # Learning vocabulary weights and transforming every document in one sparse operation
        all_vectors = self.vectorizer.fit_transform(all_documents)
        # Splitting the shared matrix back into resume and job sections by row count
        self.resume_data = resume_data
        self.job_data = job_data
        self.resume_vectors = all_vectors[: len(resume_data)]
        self.job_vectors = all_vectors[len(resume_data) :]

    def create_query_vector(
        self,
        resume_index: Optional[int],
        external_resume_text: Optional[str],
    ):
        """Creating a query vector from a dataset resume or external resume."""

        # Preventing query transformation before the shared vocabulary has been fitted
        if self.resume_data is None or self.resume_vectors is None:
            raise RuntimeError("Fitting the recommendation model is required before creating a query.")

        # Transforming a personal resume without adding it to persistent output files
        if external_resume_text is not None:
            cleaned_resume = clean_text(external_resume_text)
            if len(cleaned_resume) < 30:
                raise ValueError("The supplied resume contains too little usable text after cleaning.")
            self.query_text = cleaned_resume
            return self.vectorizer.transform([cleaned_resume]), "External resume"

        # Defaulting to the first cleaned dataset row for reproducible demonstrations
        selected_index = 0 if resume_index is None else resume_index
        if selected_index < 0 or selected_index >= len(self.resume_data):
            raise IndexError(
                f"Resume index must be between 0 and {len(self.resume_data) - 1} after cleaning."
            )
        category = str(self.resume_data.loc[selected_index, "resume_category"])
        self.query_text = str(self.resume_data.loc[selected_index, "resume_text"])
        return self.resume_vectors[selected_index], f"Dataset resume {selected_index} ({category})"

    def matching_terms(self, query_vector, job_index: int, term_limit: int = 8) -> list[tuple[str, float]]:
        """Calculating shared weighted terms for explaining one match."""

        if self.job_vectors is None:
            raise RuntimeError("Fitting the recommendation model is required before explaining matches.")
        # Multiplying sparse TF-IDF weights to measure each shared term's contribution
        feature_names = np.asarray(self.vectorizer.get_feature_names_out())
        contribution = query_vector.multiply(self.job_vectors[job_index]).toarray().ravel()
        # Keeping only the strongest positive shared terms for a compact explanation
        ranked = np.argsort(contribution)[::-1]
        ranked = ranked[contribution[ranked] > 0][:term_limit]
        return [(str(feature_names[index]), float(contribution[index])) for index in ranked]

    def recommend(
        self,
        query_vector,
        top_n: int,
        location_filter: Optional[str] = None,
        title_filter: Optional[str] = None,
        source_filter: Optional[str] = None,
    ) -> tuple[pd.DataFrame, np.ndarray, pd.DataFrame]:
        """Ranking eligible jobs and returning recommendations with explanations."""

        # Requiring fitted job vectors before applying filters and similarity calculations
        if self.job_data is None or self.job_vectors is None:
            raise RuntimeError("Fitting the recommendation model is required before ranking jobs.")
        if top_n < 1:
            raise ValueError("Top-N must be at least 1.")

        # Starting with every job eligible before applying optional contains filters
        eligible = np.ones(len(self.job_data), dtype=bool)
        if location_filter:
            eligible &= self.job_data["job_location"].str.contains(
                location_filter, case=False, regex=False, na=False
            ).to_numpy()
        if title_filter:
            eligible &= self.job_data["job_title"].str.contains(
                title_filter, case=False, regex=False, na=False
            ).to_numpy()
        if source_filter:
            eligible &= self.job_data["job_source"].str.contains(
                source_filter, case=False, regex=False, na=False
            ).to_numpy()

        # Converting the Boolean mask into source row positions used by the sparse matrix
        eligible_indices = np.flatnonzero(eligible)
        if len(eligible_indices) == 0:
            raise ValueError("No jobs matched the supplied title, location, and source filters.")

        # Calculating resume-to-job cosine similarity across all remaining sparse vectors
        scores = cosine_similarity(query_vector, self.job_vectors[eligible_indices]).ravel()
        # Sorting descending with a stable algorithm so equal scores remain reproducible
        ranked_positions = np.argsort(-scores, kind="stable")[: min(top_n, len(scores))]
        ranked_job_indices = eligible_indices[ranked_positions]

        result_columns = [
            "job_id",
            "job_title",
            "job_company",
            "job_location",
            "job_source",
            "job_url",
            "job_skills",
            "job_description_raw",
            "job_posted_at",
            "job_expires_at",
        ]
        # Copying human-readable fields before adding rank and model score columns
        recommendations = self.job_data.loc[ranked_job_indices, result_columns].copy()
        recommendations.insert(0, "rank", np.arange(1, len(recommendations) + 1))
        recommendations["cosine_similarity"] = scores[ranked_positions]

        # Preparing row-level and compact string explanations for every selected job
        explanation_rows: list[dict[str, object]] = []
        matched_term_strings: list[str] = []
        matched_skill_strings: list[str] = []
        missing_skill_strings: list[str] = []
        skill_coverages: list[float] = []
        # Extracting resume skills once before comparing them with each recommendation
        resume_skills = extract_known_skills(self.query_text)
        for rank, job_index in enumerate(ranked_job_indices, start=1):
            # Collecting weighted terms from the model and literal skills from the vocabulary
            terms = self.matching_terms(query_vector, int(job_index))
            matched_term_strings.append(", ".join(term for term, _ in terms))
            job_text = self.job_data.loc[job_index, "job_document_raw"]
            job_skills = extract_known_skills(job_text)
            matched_skills = sorted(resume_skills.intersection(job_skills))
            missing_skills = sorted(job_skills.difference(resume_skills))
            # Reporting coverage as an explanation without changing the cosine ranking
            skill_coverages.append(len(matched_skills) / len(job_skills) if job_skills else np.nan)
            matched_skill_strings.append(", ".join(matched_skills))
            missing_skill_strings.append(", ".join(missing_skills[:10]))
            # Storing one detailed row per contributing term for downloadable evidence
            for term, contribution in terms:
                explanation_rows.append(
                    {
                        "rank": rank,
                        "job_id": self.job_data.loc[job_index, "job_id"],
                        "job_title": self.job_data.loc[job_index, "job_title"],
                        "term": term,
                        "contribution": contribution,
                    }
                )
        recommendations["matched_terms"] = matched_term_strings
        recommendations["matched_skills"] = matched_skill_strings
        recommendations["missing_skills"] = missing_skill_strings
        recommendations["skill_coverage"] = skill_coverages
        return recommendations.reset_index(drop=True), scores, pd.DataFrame(explanation_rows)
