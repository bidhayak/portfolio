"""Browser-only input/output adapter around the unchanged capstone engine."""
import io
import json
import pandas as pd
from engine import ModelSettings, JobRecommendationModel, clean_text, extract_known_skills, prepare_job_data


def match_jobs(payload_json):
    payload = json.loads(payload_json)
    resume = str(payload.get('resume', ''))
    if len(resume) > 30000 or len(clean_text(resume)) < 30:
        raise ValueError('Please enter between 30 and 30,000 readable résumé characters.')
    if payload.get('csv'):
        raw = pd.read_csv(io.StringIO(payload['csv']), nrows=501)
        if len(raw) > 500:
            raise ValueError('Please use a CSV with 500 job rows or fewer for the browser edition.')
    else:
        raw = pd.DataFrame(payload['jobs'])
    jobs = prepare_job_data(raw)
    if len(jobs) < 2:
        raise ValueError('Please provide at least two distinct job descriptions to compare.')
    resumes = pd.DataFrame({'resume_text': [clean_text(resume)], 'resume_category': ['Visitor input']})
    model = JobRecommendationModel(ModelSettings(min_df=1, max_df=1.0, max_jobs=len(jobs), max_resumes=1))
    model.fit(resumes, jobs)
    query, _ = model.create_query_vector(resume_index=None, external_resume_text=resume)
    results, scores, _ = model.recommend(query, top_n=int(payload.get('top_n', 5)), location_filter=payload.get('location') or None, title_filter=payload.get('title') or None)
    rows = json.loads(results.to_json(orient='records'))
    return json.dumps({'results': rows, 'eligible': len(scores), 'job_count': len(jobs), 'skills': sorted(extract_known_skills(resume))})
