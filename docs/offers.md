# Selection and offers

Only ADMIN can move an application to `SELECTED`. Only an application in `SELECTED` can receive a draft offer. Issuing a draft offer moves the application to `OFFERED` and records that transition in the application timeline.

An offer includes its application, candidate, company and job (derived from the application), salary/package and currency, joining date, status, optional offer letter reference, issue timestamp, and optional expiry timestamp. Statuses are `DRAFT`, `ISSUED`, `ACCEPTED`, `DECLINED`, and `EXPIRED`.

- ADMIN can create a draft for a selected application, issue it, expire an active offer, and view all offers.
- STUDENT can view only their own issued or terminal offers and accept or decline an issued offer. Drafts remain hidden until issued. An expired offer cannot be accepted or declined.
- RECRUITER can view offers only for job drives belonging to their company. Recruiters cannot create, issue, expire, or respond to offers.
- Only one active (`DRAFT` or `ISSUED`) offer can exist for an application at a time. The database enforces this with a partial unique index. Terminal offers remain available as history.
- When a candidate accepts an offer, an administrator can later move the application to `JOINED`. `OFFERED` cannot be set directly through application status updates; it is set as part of issue.
- Overdue issued offers are marked `EXPIRED` when offers are listed or a candidate attempts to respond.

## API

| Method | Endpoint | Access |
| --- | --- | --- |
| POST | `/api/offers` | ADMIN; create draft for SELECTED application |
| GET | `/api/offers` | ADMIN all, STUDENT own, RECRUITER company-scoped |
| GET | `/api/offers/{id}` | Same scoped access |
| POST | `/api/offers/{id}/issue` | ADMIN |
| PATCH | `/api/offers/{id}/status` | ADMIN; expire an active offer |
| POST | `/api/offers/{id}/respond` | Owning STUDENT; accept or decline |
