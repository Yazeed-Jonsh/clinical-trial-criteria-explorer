# Clinical Trial Criteria Explorer

- Author: Yazeed-Jonsh
- Status: Draft; Overview and Goals awaiting author review
- Date: 2026-11-07
- Predecessor: [discussion_summary.md](discussion_summary.md)
- EGM stage: initial product definition; architecture and implementation plan pending

## Overview

Build a small application that helps a reader find and understand the eligibility criteria recorded for public clinical trials. A reader can search a fixed collection of studies, inspect inclusion and exclusion requirements, ask a question about a selected study, and compare two studies. Each explanation includes the original wording and a link to the study record.

The proposed first reader is a student or researcher exploring trial records. This is a portfolio and learning application. It has not been clinically validated.

The proposed first collection contains about 50 type 2 diabetes studies from ClinicalTrials.gov. The collection is a reproducible sample, not a complete inventory of trials. Show the snapshot date so a reader can distinguish the stored evidence from current information.

## The Problem

Criteria are written as free text and can contain multiple conditions, numeric thresholds, exceptions, and nested requirements. A reader comparing records must repeatedly find the relevant wording and keep the source associated with each statement.

The application will make that evidence easier to locate. Its central failure risk is changing the meaning when explaining a requirement: dropping a negation, changing a threshold, or turning missing information into a fact. Search quality and preservation of meaning must therefore be measured separately.

The strongest alternative is to use ClinicalTrials.gov directly. This project must demonstrate useful evidence retrieval and comparison on a small benchmark rather than claim it improves clinical decision making.

## Goals and observable acceptance criteria

- G1 — Traceable records: every stored study has its NCT ID, source URL, source update date when supplied, retrieval timestamp, and original eligibility text. Missing fields remain explicit.
- G2 — Search: return ranked study results with evidence snippets and IDs. A small labeled question set measures whether relevant evidence appears in the first five results. Set a performance target after measuring the baseline.
- G3 — Faithful explanations: each factual statement about a criterion points to an exact supporting passage. Retain negations, quantities, units, and exceptions. Mark ambiguous statements for review rather than guessing.
- G4 — Comparison: show evidence from each of two selected studies separately. An absent criterion is described as not stated in the stored record.
- G5 — Uncertainty: questions without supporting evidence receive an explicit missing-information response. Every designated unanswerable benchmark case must exercise this behavior before release.
- G6 — Appropriate boundary: participation questions explain that the study team must confirm eligibility. Use public records and fictional test examples.
- G7 — Reproducibility: record the data selection, snapshot date, configuration, and commands needed to reproduce evaluation. Publish actual scores with denominators and a list of observed failures.
- G8 — Learning: for each implemented milestone, the author can explain its purpose, the relevant code path, and one failure case. Record a short explanation in the learning notes.

## Non-Goals

- Deciding an individual's eligibility, recommending treatment, or enrolling participants.
- Collecting real patient records or operating a clinical service.
- Claiming live or comprehensive trial coverage from a saved sample.
- Model fine-tuning, multiple agent frameworks, or large-scale deployment during this first version.

## Five starter evaluation questions

These are question templates, not answered benchmark cases. On Day 2, bind them to actual study IDs and manually verify the expected source passages.

1. What minimum and maximum ages are stated for study A? Preserve units and record any missing limit.
2. What does study A explicitly say about insulin use? Return its wording or state that the record does not answer.
3. How do the stated HbA1c requirements differ between studies A and B? Preserve thresholds, operators, and units.
4. Which studies in this sample explicitly mention kidney-related exclusion criteria? Cite each matching passage; do not infer eligibility.
5. Does study A require a laboratory threshold that its record does not mention? The expected response is missing information.

## Open Questions

- Confirm the proposed reader, condition, and sample size during this section's review.
- Verify API access, data selection, and difficult records before promising the complete ten-session scope.
- Select retrieval, storage, model, and interface choices in the next design stage after checking local resources and cost constraints.
- Define the evaluation set and how the author will review criteria fidelity. A developer review is not clinical validation.

## Next sections

Critical user journeys, architecture, alternatives, detailed file-level tasks, and verification commands will be drafted after author review of Overview and Goals. No EGM Goldfish review has run.

*Drafted with EGM*
