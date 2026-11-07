# Clinical Trial Criteria Explorer

A learning project by Yazeed-Jonsh for exploring public clinical trial eligibility criteria with traceable evidence.

The planned application searches trial records, explains inclusion and exclusion criteria, and compares two studies. Each explanation points back to its supporting source text. Study teams determine participation eligibility.

## Current work

Day 1: product specification and project setup. The application, dataset, tests, and evaluation results have not been implemented yet.

- [Discussion context](discussion_summary.md): decisions and constraints from the planning conversation.
- [Design draft](design_draft.md): Overview and Goals, Technical Plan, and Alternatives approved; Detailed Implementation awaiting review.
- [Tasks and learning record](TASKS.md): progress and completion evidence.
- [Agent instructions](AGENTS.md): how coding sessions should work.

## Planned data

ClinicalTrials.gov public study records. The initial proposal is about 50 type 2 diabetes studies. Day 2 will verify the API, select records, and save a reproducible snapshot with identifiers and retrieval dates.

References:

- [API documentation](https://clinicaltrials.gov/data-api/api)
- [Study data structure](https://clinicaltrials.gov/data-api/about-api/study-data-structure)
- [Participation and eligibility questions](https://clinicaltrials.gov/find-studies/for-patients/common-questions)

## Development approach

Use EGM to develop and review the design. Implement one small task at a time, verify observable behavior, review the change, and record evidence before committing a milestone. Budget: ten sessions of about one hour; actual effort will be recorded.

This repository currently contains documentation only. Setup and run commands will be added when working software exists.
