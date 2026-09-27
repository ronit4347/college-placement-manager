# Placement eligibility engine

The reusable evaluator lives in `backend/app/services/eligibility.py`. It takes a persisted `Student` profile and a `JobDrive`, evaluates every configured criterion, and returns an `EligibilityResponse` with `eligible` and a list of human-readable `reasons`. The evaluator is kept in the service layer so a future application-submission service can call the same rule set before accepting an application.

## Business rules

- Minimum CGPA is inclusive: a student meets the condition when their CGPA is greater than or equal to the drive minimum.
- Maximum backlogs is inclusive: the student's backlog count must be less than or equal to the configured maximum.
- Allowed branch matching trims whitespace and ignores letter case. A null or empty branch list means no branch restriction.
- Graduation year must match the configured year exactly.
- Required skills are matched by name after trimming and ignoring letter case. A student needs every required skill. An empty requirement list imposes no skill condition.
- A missing job criterion imposes no restriction. With no configured criteria the result is eligible with no reasons.
- If a criterion is configured and the student's corresponding data is missing, the student is not eligible and receives a reason naming the missing information. If the student profile is absent entirely, the result is not eligible whenever the drive has requirements.
- All failed or missing-data criteria are returned together; the evaluator does not stop after the first failure.
- Student-supplied profile values are never accepted by the eligibility endpoint. Evaluation uses the authenticated student's saved profile and the saved drive requirements.

## API

`GET /api/job-drives/{job_drive_id}/eligibility` is restricted to the authenticated `STUDENT` role. It is available only for published drives the student can view. Example responses:

```json
{"eligible": true, "reasons": []}
```

```json
{
  "eligible": false,
  "reasons": [
    "Minimum CGPA required is 7.5; student has 7.2.",
    "Maximum backlogs allowed is 1; student has 2 backlogs."
  ]
}
```

`GET /api/job-drives/eligible` is a student-only, server-side filtered search for currently open published drives that match the student's saved eligibility criteria. It accepts the same keyword, location, employment type, and graduation year filters used by the published-drive search. Expired deadlines and inactive companies are excluded. This endpoint powers the dashboard's eligible-jobs search without making one eligibility request per result.

The frontend displays the result and all reasons on the student's job drive details page. Application submission uses the same server-side evaluator and rejects ineligible students before creating an application.
