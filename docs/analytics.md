# Admin placement analytics

The ADMIN-only analytics endpoints calculate their output from live database rows. No dashboard figures or chart series are seeded in the frontend.

## Endpoints

- `GET /api/admin/analytics/dashboard` returns the KPI values and all five chart datasets.
- `GET /api/admin/analytics/filters` returns graduation years, branches, and companies currently present in the database.

The dashboard endpoint accepts optional `graduation_year`, `branch`, `company_id`, `date_from`, and `date_to` query parameters. Year and branch filter the student cohort and its related applications. Company filters companies, drives, applications, and outcomes to one employer. Date bounds filter applications by their submission date, inclusively. They must be provided as ISO dates, and `date_from` cannot follow `date_to`.

## Metric definitions

- Active job drives are published drives with an application deadline in the future.
- Shortlisted candidates count applications that reached shortlist, including applications that advanced to later stages.
- Interviews count non-cancelled interview rounds; the funnel's interviewed stage counts distinct applications that reached the interview stage.
- Selected candidates include applications currently selected, offered, or joined.
- Offers count non-draft offers. Package distribution includes issued offers and their outcomes denominated in INR, grouped into annual salary bands.
- Placements count distinct students whose application reached `JOINED`. Placement rate is those students divided by registered students in the selected year/branch cohort.
- Monthly placement activity counts joined status-history events for the latest twelve calendar months.

All charts follow the same selected application cohort, employer, and submission-date filters as the application outcomes. The dashboard shows loading placeholders, per-chart empty states, retryable request errors, and a resettable filter form.
