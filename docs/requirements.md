# Initial Business Problem and Requirements

## Business problem

Placement teams coordinate a multi-step process involving students, eligibility, job drives, applications, shortlisting, interviews, selections, and offers. Fragmented tracking can make it hard to maintain accurate records, coordinate stakeholders, and report outcomes.

## High-level requirements

- Provide a web application accessible to placement stakeholders.
- Eventually support STUDENT, ADMIN/PLACEMENT OFFICER, RECRUITER, and INTERVIEWER roles.
- Eventually coordinate the lifecycle: Student → Eligibility → Job Drive → Application → Shortlisting → Interview → Selection → Offer → Placement Analytics.
- Provide a backend REST API and PostgreSQL-backed persistence.
- Keep configuration and secrets outside source code using environment variables.
- For the foundation milestone only, provide a responsive frontend shell, backend health endpoint, and basic frontend-to-backend connectivity status.

## Out of scope for this milestone

Authentication, domain models, database migrations, student/company/job-drive management, applications, interviews, offers, AI features, and analytics dashboards.
